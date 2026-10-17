from io import BytesIO
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import ActivityLog, Role, User
from .excel_utils import detect_column_mapping, read_excel_file
from .models import ExcelImport, Lead


class FlexibleExcelImportTests(SimpleTestCase):
    def test_finds_headers_on_data_sheet_after_metadata_rows(self):
        workbook = BytesIO()
        with pd.ExcelWriter(workbook, engine='openpyxl') as writer:
            pd.DataFrame([['Instructions']]).to_excel(
                writer, index=False, header=False, sheet_name='Read Me'
            )
            pd.DataFrame([
                ['Monthly list'],
                ['Customer Name', 'Telephone Number', 'Email Address'],
                ['Ada Example', '555-123-4567', 'ada@example.com'],
            ]).to_excel(writer, index=False, header=False, sheet_name='Data')
        workbook.seek(0)
        workbook.name = 'leads.xlsx'

        dataframe, error = read_excel_file(workbook)

        self.assertIsNone(error)
        self.assertEqual(dataframe.iloc[0]['Customer Name'], 'Ada Example')
        mapping = detect_column_mapping(dataframe.columns)
        self.assertEqual(mapping['name'], 'Customer Name')
        self.assertEqual(mapping['phone'], 'Telephone Number')

    def test_reads_delimited_csv_with_metadata_preamble(self):
        upload = BytesIO(
            b'Export generated\r\n'
            b'Name;Mobile No.;City\r\n'
            b'Grace Hopper;5551234567;Arlington\r\n'
        )
        upload.name = 'leads.csv'

        dataframe, error = read_excel_file(upload)

        self.assertIsNone(error)
        self.assertEqual(dataframe.iloc[0]['Name'], 'Grace Hopper')
        self.assertEqual(detect_column_mapping(dataframe.columns)['phone'], 'Mobile No.')


class ExcelImportServerlessTests(TestCase):
    def test_admin_can_delete_one_import_batch_without_deleting_other_leads(self):
        admin = User.objects.create_user(
            email='admin@example.com', password='password', role=Role.ADMIN,
        )
        import_obj = ExcelImport.objects.create(
            uploaded_by=admin,
            file_name='leads.xlsx',
            total_rows=2,
            imported_rows=2,
            status=ExcelImport.ImportStatus.COMPLETED,
        )
        empty_import = ExcelImport.objects.create(
            uploaded_by=admin,
            file_name='empty.xlsx',
            imported_rows=0,
            status=ExcelImport.ImportStatus.COMPLETED,
        )
        imported_lead = Lead.objects.create(
            name='Imported Lead',
            phone='555-123-4567',
            source='EXCEL',
            created_by=admin,
            excel_import=import_obj,
        )
        other_lead = Lead.objects.create(
            name='Manual Lead',
            phone='555-765-4321',
            created_by=admin,
        )
        self.client.force_login(admin)

        history_response = self.client.get(reverse('leads:import_history'))
        self.assertContains(history_response, 'Delete Leads')
        self.assertContains(history_response, 'Current Leads')
        upload_response = self.client.get(reverse('leads:excel_upload'))
        self.assertEqual(len(upload_response.context['recent_imports']), 2)
        self.assertContains(upload_response, '<i class="bi bi-trash"></i>', count=2)
        self.assertContains(upload_response, 'name="return_to" value="upload"', count=2)

        response = self.client.post(
            reverse('leads:delete_imported_leads', args=[import_obj.pk]),
            {'return_to': 'upload'},
        )

        self.assertRedirects(response, reverse('leads:excel_upload'))
        self.assertFalse(Lead.objects.filter(pk=imported_lead.pk).exists())
        self.assertTrue(Lead.objects.filter(pk=other_lead.pk).exists())
        self.assertFalse(ExcelImport.objects.filter(pk=import_obj.pk).exists())
        empty_import_response = self.client.post(
            reverse('leads:delete_imported_leads', args=[empty_import.pk]),
            {'return_to': 'upload'},
        )
        self.assertRedirects(empty_import_response, reverse('leads:excel_upload'))
        self.assertFalse(ExcelImport.objects.filter(pk=empty_import.pk).exists())
        self.assertNotContains(
            self.client.get(reverse('leads:import_history')), 'Delete Leads'
        )
        self.assertTrue(ActivityLog.objects.filter(
            user=admin,
            action=ActivityLog.ActionType.DELETE,
            model_name='ExcelImport',
            object_id=str(import_obj.pk),
        ).exists())

    def test_non_admin_cannot_delete_imported_leads(self):
        admin = User.objects.create_user(
            email='admin@example.com', password='password', role=Role.ADMIN,
            username='admin',
        )
        caller = User.objects.create_user(
            email='caller@example.com', password='password', role=Role.CALLING,
            username='caller',
        )
        import_obj = ExcelImport.objects.create(
            uploaded_by=admin,
            file_name='leads.xlsx',
            imported_rows=1,
        )
        lead = Lead.objects.create(
            name='Imported Lead',
            phone='555-123-4567',
            source='EXCEL',
            created_by=admin,
            excel_import=import_obj,
        )
        self.client.force_login(caller)

        response = self.client.post(
            reverse('leads:delete_imported_leads', args=[import_obj.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Lead.objects.filter(pk=lead.pk).exists())

    def test_delete_matches_legacy_import_leads_without_batch_foreign_key(self):
        admin = User.objects.create_user(
            email='admin@example.com', password='password', role=Role.ADMIN,
        )
        workbook = BytesIO()
        pd.DataFrame([{
            'Name': 'Talwara Customer',
            'Phone': '555-123-4567',
        }]).to_excel(workbook, index=False)
        import_obj = ExcelImport.objects.create(
            uploaded_by=admin,
            file_name='talwara sheet.xlsx',
            file_content=workbook.getvalue(),
            column_mapping={'name': 'Name', 'phone': 'Phone'},
            imported_rows=1,
            status=ExcelImport.ImportStatus.COMPLETED,
        )
        legacy_lead = Lead.objects.create(
            name='Talwara Customer',
            phone='5551234567',
            source='EXCEL',
            created_by=admin,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('leads:delete_imported_leads', args=[import_obj.pk]),
        )

        self.assertRedirects(response, reverse('leads:import_history'))
        self.assertFalse(Lead.objects.filter(pk=legacy_lead.pk).exists())
        self.assertFalse(ExcelImport.objects.filter(pk=import_obj.pk).exists())

    def test_does_not_remove_import_history_when_rows_cannot_be_matched(self):
        admin = User.objects.create_user(
            email='admin@example.com', password='password', role=Role.ADMIN,
        )
        import_obj = ExcelImport.objects.create(
            uploaded_by=admin,
            file_name='legacy.xlsx',
            imported_rows=5,
            status=ExcelImport.ImportStatus.COMPLETED,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('leads:delete_imported_leads', args=[import_obj.pk]),
        )

        self.assertRedirects(response, reverse('leads:import_history'))
        self.assertTrue(ExcelImport.objects.filter(pk=import_obj.pk).exists())

    def test_upload_and_confirm_do_not_write_to_local_file_storage(self):
        admin = User.objects.create_user(
            email='admin@example.com', password='password', role=Role.ADMIN,
        )
        self.client.force_login(admin)

        workbook = BytesIO()
        pd.DataFrame([{
            'Name': 'Ada Example',
            'Phone': '555-123-4567',
        }]).to_excel(workbook, index=False)
        upload = SimpleUploadedFile(
            'leads.xlsx', workbook.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        with patch(
            'django.core.files.storage.FileSystemStorage._save',
            side_effect=AssertionError('Excel import must not write local files'),
        ):
            response = self.client.post(reverse('leads:excel_upload'), {'excel_file': upload})
            self.assertEqual(response.status_code, 200)

            import_obj = ExcelImport.objects.get()
            self.assertEqual(import_obj.file_content, workbook.getvalue())

            response = self.client.post(reverse('leads:excel_import'), {
                'map_name': 'Name',
                'map_phone': 'Phone',
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lead.objects.filter(name='Ada Example').count(), 1)