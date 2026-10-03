from io import BytesIO
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Role, User
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