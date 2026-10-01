"""
Excel import/export utilities using pandas + openpyxl.
"""
import csv
import re
import pandas as pd
from io import BytesIO, StringIO
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile

# Expected columns and their aliases
COLUMN_ALIASES = {
    'name': ['name', 'lead name', 'contact name', 'full name', 'customer name', 'client name'],
    'company': ['company', 'company name', 'organisation', 'organization', 'firm', 'business name'],
    'phone': ['phone', 'phone number', 'phone no', 'mobile', 'mobile number', 'mobile no', 'cell phone', 'telephone', 'contact', 'contact number', 'contact no'],
    'alternate_phone': ['alternate phone', 'alternate phone number', 'alt phone', 'other phone', 'phone 2', 'secondary phone'],
    'email': ['email', 'email address', 'e-mail'],
    'location': ['location', 'address', 'area'],
    'city': ['city', 'town'],
    'state': ['state', 'province'],
    'remarks': ['remarks', 'notes', 'comment', 'comments', 'description'],
    'source': ['source', 'lead source'],
    'product_interest': ['product', 'product interest', 'interest', 'requirement'],
    'budget': ['budget', 'price range'],
    'website': ['website', 'web', 'url'],
}

REQUIRED_COLUMNS = ['name', 'phone']
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?[\d\s\-\(\)]{7,20}$')


def detect_column_mapping(df_columns):
    """Auto-detect CRM fields from common header variants."""
    mapping = {}
    aliases_normalized = {
        field: {_normalize_header(alias) for alias in aliases}
        for field, aliases in COLUMN_ALIASES.items()
    }

    for field, aliases in COLUMN_ALIASES.items():
        for col in df_columns:
            normalized = _normalize_header(col)
            if any(
                normalized == alias or f' {alias} ' in f' {normalized} '
                for alias in aliases_normalized[field]
            ):
                mapping[field] = col
                break

    return mapping


def _normalize_header(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value).casefold()).strip()


def _find_header_row(raw_df):
    """Find a likely header row near the top of an exported spreadsheet."""
    for row_index in range(min(len(raw_df), 25)):
        headers = [str(value).strip() for value in raw_df.iloc[row_index].tolist()]
        mapping = detect_column_mapping(headers)
        if all(field in mapping for field in REQUIRED_COLUMNS):
            return row_index
    return None


def _dataframe_from_raw(raw_df, header_row):
    headers = [str(value).strip() for value in raw_df.iloc[header_row].tolist()]
    df = raw_df.iloc[header_row + 1:].copy()
    df.columns = headers
    df = df.replace(r'^\s*$', pd.NA, regex=True).dropna(how='all').fillna('')
    df = df.reset_index(drop=True)
    df.attrs['header_row_number'] = header_row + 1
    return df


def _detect_csv_separator(buf, encoding):
    delimiters = ',;\t|'
    sample = buf.read(65536).decode(encoding)
    buf.seek(0)
    lines = [
        line for line in sample.splitlines()
        if any(delimiter in line for delimiter in delimiters)
    ]
    if not lines:
        return ','

    try:
        return csv.Sniffer().sniff('\n'.join(lines[:25]), delimiters=delimiters).delimiter
    except csv.Error:
        return max(delimiters, key=lambda delimiter: sum(line.count(delimiter) for line in lines))


def read_excel_file(file_obj):
    """
    Read an Excel or CSV file into a pandas DataFrame.
    Returns (df, error_message).
    """
    try:
        filename = getattr(file_obj, 'name', '')
        if isinstance(file_obj, InMemoryUploadedFile):
            content = file_obj.read()
            file_obj.seek(0)
            buf = BytesIO(content)
        else:
            buf = file_obj

        if filename.lower().endswith('.csv'):
            try:
                encoding = 'utf-8-sig'
                separator = _detect_csv_separator(buf, encoding)
                raw_df = pd.DataFrame(
                    csv.reader(StringIO(buf.read().decode(encoding)), delimiter=separator)
                )
            except UnicodeDecodeError:
                buf.seek(0)
                encoding = 'cp1252'
                separator = _detect_csv_separator(buf, encoding)
                raw_df = pd.DataFrame(
                    csv.reader(StringIO(buf.read().decode(encoding)), delimiter=separator)
                )
            header_row = _find_header_row(raw_df)
            df = _dataframe_from_raw(raw_df, header_row if header_row is not None else 0)
        else:
            workbook = pd.ExcelFile(buf)
            selected_sheet = workbook.sheet_names[0]
            header_row = None
            for sheet_name in workbook.sheet_names:
                candidate = workbook.parse(
                    sheet_name=sheet_name, header=None, nrows=25,
                    dtype=str, keep_default_na=False,
                )
                candidate_header = _find_header_row(candidate)
                if candidate_header is not None:
                    selected_sheet = sheet_name
                    header_row = candidate_header
                    break
            raw_df = workbook.parse(
                sheet_name=selected_sheet, header=None, dtype=str,
                keep_default_na=False,
            )
            if header_row is None:
                header_row = _find_header_row(raw_df)
            df = _dataframe_from_raw(raw_df, header_row if header_row is not None else 0)

        return df, None
    except Exception as e:
        return None, str(e)


def validate_and_process_rows(df, column_mapping):
    """
    Validate rows using the given column mapping.
    Returns (valid_rows, invalid_rows, duplicate_phones).
    valid_rows: list of dicts ready for Lead creation.
    invalid_rows: list of {'row': int, 'reason': str, 'data': dict}.
    """
    from .models import Lead

    # Fetch existing phones once for duplicate detection
    existing_phones = set(
        Lead.objects.values_list('phone', flat=True)
    )
    seen_phones_in_file = set()

    valid_rows = []
    invalid_rows = []

    for idx, row in df.iterrows():
        row_num = idx + df.attrs.get('header_row_number', 1) + 1
        row_data = {}
        errors = []

        # Map columns
        for field, col in column_mapping.items():
            if col and col in df.columns:
                val = str(row.get(col, '')).strip()
                if val.lower() in ('nan', 'none', ''):
                    val = ''
                row_data[field] = val

        # Required: name
        if not row_data.get('name'):
            errors.append('Missing name')

        # Required: phone
        phone = row_data.get('phone', '').strip()
        if not phone:
            errors.append('Missing phone number')
        elif not PHONE_REGEX.match(phone):
            errors.append(f'Invalid phone format: {phone}')
        else:
            # Normalize phone
            phone_normalized = re.sub(r'[\s\-\(\)]', '', phone)
            row_data['phone'] = phone_normalized

            # Duplicate in DB
            if phone_normalized in existing_phones:
                errors.append(f'Duplicate phone (already in DB): {phone_normalized}')
                row_data['is_duplicate'] = True
            # Duplicate in this file
            elif phone_normalized in seen_phones_in_file:
                errors.append(f'Duplicate phone (in this file): {phone_normalized}')
                row_data['is_duplicate'] = True
            else:
                seen_phones_in_file.add(phone_normalized)
                row_data['is_duplicate'] = False

        # Email validation (optional field)
        email = row_data.get('email', '')
        if email and not EMAIL_REGEX.match(email):
            errors.append(f'Invalid email: {email}')
            row_data['email'] = ''

        if errors:
            invalid_rows.append({
                'row': row_num,
                'errors': errors,
                'data': row_data,
            })
        else:
            valid_rows.append(row_data)

    return valid_rows, invalid_rows


def import_leads_from_rows(valid_rows, import_obj, created_by, assigned_to=None):
    """
    Bulk-create Lead objects from validated rows.
    Returns count of imported rows.
    """
    from .models import Lead, LeadSource

    leads_to_create = []
    for row in valid_rows:
        if row.get('is_duplicate'):
            continue
        lead = Lead(
            name=row.get('name', ''),
            company=row.get('company', ''),
            phone=row.get('phone', ''),
            alternate_phone=row.get('alternate_phone', ''),
            email=row.get('email', ''),
            location=row.get('location', ''),
            city=row.get('city', ''),
            state=row.get('state', ''),
            remarks=row.get('remarks', ''),
            product_interest=row.get('product_interest', ''),
            budget=row.get('budget', ''),
            website=row.get('website', ''),
            source=LeadSource.EXCEL_UPLOAD,
            assigned_to=assigned_to,
            created_by=created_by,
            excel_import=import_obj,
        )
        leads_to_create.append(lead)

    Lead.objects.bulk_create(leads_to_create, batch_size=500)
    return len(leads_to_create)


def export_leads_to_excel(queryset):
    """
    Export a Lead queryset to an Excel file.
    Returns BytesIO buffer.
    """
    data = []
    for lead in queryset.select_related('assigned_to'):
        data.append({
            'Name': lead.name,
            'Company': lead.company,
            'Phone': lead.phone,
            'Alternate Phone': lead.alternate_phone,
            'Email': lead.email,
            'Location': lead.location,
            'City': lead.city,
            'State': lead.state,
            'Source': lead.get_source_display(),
            'Status': lead.get_status_display(),
            'Assigned To': lead.assigned_to.full_name if lead.assigned_to else '',
            'Remarks': lead.remarks,
            'Product Interest': lead.product_interest,
            'Budget': lead.budget,
            'Last Called': lead.last_called_at.strftime('%Y-%m-%d %H:%M') if lead.last_called_at else '',
            'Created At': lead.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    df = pd.DataFrame(data)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leads')
        # Auto-size columns
        worksheet = writer.sheets['Leads']
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    buf.seek(0)
    return buf
