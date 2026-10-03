"""
Leads views — list, detail, create, update, Excel import/export, assignment.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from apps.accounts.permissions import admin_required, calling_required
from apps.accounts.models import User, Role, ActivityLog
from apps.accounts.views import get_client_ip
from .models import Lead, LeadAssignment, Note, ExcelImport, LeadStatus, LeadSource
from .excel_utils import (
    read_excel_file, detect_column_mapping,
    validate_and_process_rows, import_leads_from_rows,
    export_leads_to_excel, COLUMN_ALIASES,
)


# ---------------------------------------------------------------------------
# Lead List
# ---------------------------------------------------------------------------
@login_required
def lead_list(request):
    user = request.user

    if user.is_admin:
        qs = Lead.objects.select_related('assigned_to', 'created_by')
    else:
        qs = Lead.objects.filter(assigned_to=user).select_related('assigned_to')

    # Search
    search = request.GET.get('q', '')
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(company__icontains=search) |
            Q(email__icontains=search)
        )

    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    source_filter = request.GET.get('source', '')
    if source_filter:
        qs = qs.filter(source=source_filter)

    assigned_filter = request.GET.get('assigned_to', '')
    if assigned_filter and user.is_admin:
        qs = qs.filter(assigned_to_id=assigned_filter)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    qs = qs.order_by('-updated_at')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    # Stats for current filter
    stats = {
        'total': qs.count(),
        'pending': qs.filter(status=LeadStatus.PENDING).count(),
        'interested': qs.filter(status=LeadStatus.INTERESTED).count(),
        'not_interested': qs.filter(status=LeadStatus.NOT_INTERESTED).count(),
        'follow_up': qs.filter(status=LeadStatus.FOLLOW_UP).count(),
    }

    employees = User.objects.filter(role=Role.CALLING, is_active=True) if user.is_admin else []

    return render(request, 'leads/list.html', {
        'leads': page,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'assigned_filter': assigned_filter,
        'status_choices': LeadStatus.choices,
        'source_choices': LeadSource.choices,
        'employees': employees,
        'date_from': date_from,
        'date_to': date_to,
    })


# ---------------------------------------------------------------------------
# Lead Detail
# ---------------------------------------------------------------------------
@login_required
def lead_detail(request, pk):
    user = request.user
    lead = get_object_or_404(Lead, pk=pk)

    # Permission: only admin or assigned employee
    if not user.is_admin and lead.assigned_to != user:
        messages.error(request, 'You do not have permission to view this lead.')
        return redirect('leads:list')

    from apps.calling.models import CallLog, FollowUp
    calls = CallLog.objects.filter(lead=lead).select_related('employee').order_by('-started_at')
    followups = FollowUp.objects.filter(lead=lead).select_related('assigned_to').order_by('-follow_up_date')
    notes = Note.objects.filter(lead=lead).select_related('created_by').order_by('-created_at')
    assignments = LeadAssignment.objects.filter(lead=lead).select_related('assigned_to', 'assigned_by')

    return render(request, 'leads/detail.html', {
        'lead': lead,
        'calls': calls,
        'followups': followups,
        'notes': notes,
        'assignments': assignments,
        'status_choices': LeadStatus.choices,
    })


# ---------------------------------------------------------------------------
# Lead Create (manual)
# ---------------------------------------------------------------------------
@login_required
def lead_create(request):
    user = request.user
    calling_employees = User.objects.filter(role=Role.CALLING, is_active=True)

    if request.method == 'POST':
        data = request.POST
        errors = {}

        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        if not name:
            errors['name'] = 'Name is required.'
        if not phone:
            errors['phone'] = 'Phone is required.'
        elif Lead.objects.filter(phone=phone).exists():
            errors['phone'] = 'A lead with this phone number already exists.'

        if not errors:
            lead = Lead.objects.create(
                name=name,
                company=data.get('company', '').strip(),
                phone=phone,
                alternate_phone=data.get('alternate_phone', '').strip(),
                email=data.get('email', '').strip(),
                location=data.get('location', '').strip(),
                city=data.get('city', '').strip(),
                state=data.get('state', '').strip(),
                source=data.get('source', LeadSource.MANUAL),
                remarks=data.get('remarks', '').strip(),
                product_interest=data.get('product_interest', '').strip(),
                budget=data.get('budget', '').strip(),
                assigned_to_id=data.get('assigned_to') or None,
                created_by=user,
            )
            ActivityLog.objects.create(
                user=user,
                action=ActivityLog.ActionType.CREATE,
                model_name='Lead',
                object_id=str(lead.id),
                description=f'Created lead: {lead.name}',
                ip_address=get_client_ip(request),
            )
            messages.success(request, f'Lead "{lead.name}" created successfully.')
            return redirect('leads:detail', pk=lead.pk)
        else:
            return render(request, 'leads/create.html', {
                'errors': errors,
                'data': data,
                'calling_employees': calling_employees,
                'source_choices': LeadSource.choices,
            })

    return render(request, 'leads/create.html', {
        'calling_employees': calling_employees,
        'source_choices': LeadSource.choices,
    })


# ---------------------------------------------------------------------------
# Lead Update Status (AJAX)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def lead_update_status(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    user = request.user
    if not user.is_admin and lead.assigned_to != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    new_status = request.POST.get('status')
    if new_status not in [c[0] for c in LeadStatus.choices]:
        return JsonResponse({'error': 'Invalid status.'}, status=400)

    old_status = lead.status
    lead.status = new_status
    lead.save(update_fields=['status', 'updated_at'])

    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.ActionType.UPDATE,
        model_name='Lead',
        object_id=str(lead.id),
        description=f'Lead status changed: {old_status} → {new_status}',
        ip_address=get_client_ip(request),
    )
    return JsonResponse({'status': new_status, 'label': lead.get_status_display()})


# ---------------------------------------------------------------------------
# Add Note (AJAX)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def add_note(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    user = request.user
    if not user.is_admin and lead.assigned_to != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Note content is required.'}, status=400)

    note = Note.objects.create(lead=lead, created_by=user, content=content)
    return JsonResponse({
        'id': note.id,
        'content': note.content,
        'created_by': user.full_name,
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
    })


# ---------------------------------------------------------------------------
# Assign Leads (Admin)
# ---------------------------------------------------------------------------
@admin_required
def assign_leads(request):
    if request.method == 'POST':
        lead_ids = request.POST.getlist('lead_ids')
        assigned_to_id = request.POST.get('assigned_to')

        if not lead_ids or not assigned_to_id:
            messages.error(request, 'Please select leads and an employee.')
            return redirect('leads:list')

        try:
            employee = User.objects.get(pk=assigned_to_id, role=Role.CALLING)
        except User.DoesNotExist:
            messages.error(request, 'Invalid employee selected.')
            return redirect('leads:list')

        leads = Lead.objects.filter(pk__in=lead_ids)
        for lead in leads:
            lead.assigned_to = employee
            lead.save(update_fields=['assigned_to', 'updated_at'])
            LeadAssignment.objects.create(
                lead=lead,
                assigned_to=employee,
                assigned_by=request.user,
            )
            # Notification
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=employee,
                    title='New Lead Assigned',
                    message=f'Lead "{lead.name}" has been assigned to you.',
                    notification_type='LEAD_ASSIGNED',
                    related_object_id=lead.id,
                )
            except Exception:
                pass

        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.ASSIGN,
            model_name='Lead',
            description=f'Assigned {len(lead_ids)} leads to {employee.full_name}.',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'{len(lead_ids)} leads assigned to {employee.full_name}.')
        return redirect('leads:list')

    return redirect('leads:list')


# ---------------------------------------------------------------------------
# Excel Import
# ---------------------------------------------------------------------------
@admin_required
def excel_upload(request):
    """Step 1: Upload Excel and show preview with column mapping."""
    if request.method == 'POST':
        uploaded_file = request.FILES.get('excel_file')
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('leads:excel_upload')

        # Validate file extension
        filename = uploaded_file.name.lower()
        if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
            messages.error(request, 'Invalid file type. Please upload .xlsx, .xls, or .csv files.')
            return redirect('leads:excel_upload')

        # Validate file size (10 MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            messages.error(request, 'File size exceeds 10 MB limit.')
            return redirect('leads:excel_upload')

        df, error = read_excel_file(uploaded_file)
        if error:
            messages.error(request, f'Error reading file: {error}')
            return redirect('leads:excel_upload')

        if len(df) == 0:
            messages.error(request, 'The file appears to be empty.')
            return redirect('leads:excel_upload')

        if len(df) > 10000:
            messages.error(request, 'File contains more than 10,000 rows. Please split into smaller files.')
            return redirect('leads:excel_upload')

        # Auto-detect column mapping
        auto_mapping = detect_column_mapping(df.columns.tolist())
        mapping_options = [
            {
                'field': field,
                'required': field in ('name', 'phone'),
                'options': [
                    {
                        'column': column,
                        'selected': auto_mapping.get(field) == column,
                    }
                    for column in df.columns.tolist()
                ],
            }
            for field in COLUMN_ALIASES.keys()
        ]

        # Store the file in the database so it survives serverless requests.
        uploaded_file.seek(0)
        import_obj = ExcelImport.objects.create(
            uploaded_by=request.user,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
            total_rows=len(df),
            status=ExcelImport.ImportStatus.PENDING,
        )

        # Store preview in session
        preview_rows = df.head(10).to_dict('records')
        request.session['excel_import_id'] = import_obj.id
        request.session['excel_columns'] = df.columns.tolist()
        request.session['excel_auto_mapping'] = auto_mapping

        calling_employees = User.objects.filter(role=Role.CALLING, is_active=True)

        return render(request, 'leads/excel_preview.html', {
            'import_obj': import_obj,
            'columns': df.columns.tolist(),
            'mapping_options': mapping_options,
            'preview_rows': preview_rows,
            'auto_mapping': auto_mapping,
            'field_names': list(COLUMN_ALIASES.keys()),
            'calling_employees': calling_employees,
            'total_rows': len(df),
        })

    recent_imports = ExcelImport.objects.filter(
        uploaded_by=request.user
    ).order_by('-created_at')[:10]
    return render(request, 'leads/excel_upload.html', {'recent_imports': recent_imports})


@admin_required
@require_POST
def excel_import_confirm(request):
    """Step 2: Validate, detect duplicates, and import."""
    import_id = request.session.get('excel_import_id')
    if not import_id:
        messages.error(request, 'Import session expired. Please upload again.')
        return redirect('leads:excel_upload')

    import_obj = get_object_or_404(ExcelImport, pk=import_id, uploaded_by=request.user)

    # Get user-provided column mapping from POST
    column_mapping = {}
    for field in COLUMN_ALIASES.keys():
        col = request.POST.get(f'map_{field}', '')
        if col:
            column_mapping[field] = col

    if 'name' not in column_mapping or 'phone' not in column_mapping:
        messages.error(request, 'You must map at least the Name and Phone columns.')
        return redirect('leads:excel_upload')

    assigned_to_id = request.POST.get('assigned_to') or None
    assigned_to = None
    if assigned_to_id:
        try:
            assigned_to = User.objects.get(pk=assigned_to_id, role=Role.CALLING)
        except User.DoesNotExist:
            pass

    # Read from the database on serverless hosts where local media is not persistent.
    if import_obj.file_content is not None:
        from io import BytesIO
        uploaded_file = BytesIO(import_obj.file_content)
        uploaded_file.name = import_obj.file_name
    else:
        import_obj.file.seek(0)
        uploaded_file = import_obj.file

    df, error = read_excel_file(uploaded_file)
    if error:
        messages.error(request, f'Error reading file: {error}')
        return redirect('leads:excel_upload')

    # Validate
    import_obj.status = ExcelImport.ImportStatus.PROCESSING
    import_obj.column_mapping = column_mapping
    import_obj.save()

    valid_rows, invalid_rows = validate_and_process_rows(df, column_mapping)
    duplicate_count = sum(1 for r in valid_rows if r.get('is_duplicate'))

    # Import valid non-duplicate rows
    imported_count = import_leads_from_rows(valid_rows, import_obj, request.user, assigned_to)

    # Update import record
    import_obj.status = ExcelImport.ImportStatus.COMPLETED
    import_obj.valid_rows = len(valid_rows)
    import_obj.imported_rows = imported_count
    import_obj.duplicate_rows = duplicate_count
    import_obj.invalid_rows = len(invalid_rows)
    import_obj.error_details = {'invalid_rows': invalid_rows[:100]}  # cap at 100
    import_obj.completed_at = timezone.now()
    import_obj.save()

    # Clear session
    request.session.pop('excel_import_id', None)

    ActivityLog.objects.create(
        user=request.user,
        action=ActivityLog.ActionType.UPLOAD,
        model_name='ExcelImport',
        object_id=str(import_obj.id),
        description=f'Excel import: {import_obj.file_name} — {imported_count} imported, {len(invalid_rows)} invalid, {duplicate_count} duplicates.',
        ip_address=get_client_ip(request),
    )

    return render(request, 'leads/excel_result.html', {
        'import_obj': import_obj,
        'invalid_rows': invalid_rows[:50],
    })


# ---------------------------------------------------------------------------
# Excel Export
# ---------------------------------------------------------------------------
@login_required
def excel_export(request):
    user = request.user
    if user.is_admin:
        qs = Lead.objects.all()
    else:
        qs = Lead.objects.filter(assigned_to=user)

    # Apply same filters as list view
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    buf = export_leads_to_excel(qs)
    filename = f'leads_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Import History
# ---------------------------------------------------------------------------
@admin_required
def import_history(request):
    imports = ExcelImport.objects.select_related('uploaded_by').order_by('-created_at')
    paginator = Paginator(imports, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'leads/import_history.html', {'imports': page})


# ---------------------------------------------------------------------------
# API: Quick search for leads (AJAX)
# ---------------------------------------------------------------------------
@login_required
def lead_search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    user = request.user
    qs = Lead.objects.filter(
        Q(name__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q)
    )
    if not user.is_admin:
        qs = qs.filter(assigned_to=user)

    results = list(qs.values('id', 'name', 'phone', 'company', 'status')[:10])
    return JsonResponse({'results': results})
