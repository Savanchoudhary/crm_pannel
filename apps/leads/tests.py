from io import BytesIO

import pandas as pd
from django.test import SimpleTestCase

from .excel_utils import detect_column_mapping, read_excel_file


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