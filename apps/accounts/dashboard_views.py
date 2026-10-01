"""
Role-based dashboard views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from datetime import timedelta, date

from .models import User, Role, ActivityLog


@login_required
def dashboard_index(request):
    """Route user to their role-specific dashboard."""
    user = request.user
    if user.is_admin:
        return admin_dashboard(request)
    elif user.is_calling:
        return calling_dashboard(request)
    elif user.is_marketing:
        return marketing_dashboard(request)
    elif user.is_developer:
        return developer_dashboard(request)
    else:
        return admin_dashboard(request)


@login_required
def admin_dashboard(request):
    from apps.leads.models import Lead, LeadStatus
    from apps.calling.models import CallLog, FollowUp
    from apps.attendance.models import Attendance

    today = date.today()
    now = timezone.now()

    # ── Date filter ─────────────────────────────────────────────────────────
    date_range = request.GET.get('range', 'today')
    if date_range == 'yesterday':
        start = today - timedelta(days=1)
        end = today - timedelta(days=1)
    elif date_range == 'week':
        start = today - timedelta(days=today.weekday())
        end = today
    elif date_range == 'month':
        start = today.replace(day=1)
        end = today
    elif date_range == 'custom':
        try:
            from datetime import datetime
            start = datetime.strptime(request.GET.get('start', str(today)), '%Y-%m-%d').date()
            end = datetime.strptime(request.GET.get('end', str(today)), '%Y-%m-%d').date()
        except Exception:
            start = end = today
    else:  # today
        start = end = today

    # ── Employee Stats ───────────────────────────────────────────────────────
    total_employees = User.objects.filter(is_active=True, is_superuser=False).count()
    calling_count = User.objects.filter(role=Role.CALLING, is_active=True).count()
    marketing_count = User.objects.filter(role=Role.MARKETING, is_active=True).count()
    developer_count = User.objects.filter(role=Role.DEVELOPER, is_active=True).count()

    # ── Lead Stats ───────────────────────────────────────────────────────────
    total_leads = Lead.objects.count()
    interested = Lead.objects.filter(status=LeadStatus.INTERESTED).count()
    not_interested = Lead.objects.filter(status=LeadStatus.NOT_INTERESTED).count()
    pending_leads = Lead.objects.filter(status=LeadStatus.PENDING).count()

    # ── Call Stats (filtered by date range) ──────────────────────────────────
    calls_in_range = CallLog.objects.filter(
        started_at__date__gte=start, started_at__date__lte=end
    )
    calls_in_selected_range = calls_in_range.count()
    calls_completed = calls_in_range.filter(result__in=['COMPLETED', 'INTERESTED', 'NOT_INTERESTED']).count()
    calls_pending = Lead.objects.filter(status=LeadStatus.PENDING).count()

    # ── Follow-ups ────────────────────────────────────────────────────────────
    followups_today = FollowUp.objects.filter(
        follow_up_date=today, is_completed=False
    ).count()
    overdue_followups = FollowUp.objects.filter(
        follow_up_date__lt=today, is_completed=False
    ).count()

    # ── Conversion rate ───────────────────────────────────────────────────────
    conversion_rate = 0
    if total_leads > 0:
        conversion_rate = round((interested / total_leads) * 100, 1)

    # ── Today's attendance ────────────────────────────────────────────────────
    today_attendance = Attendance.objects.filter(
        date=today
    ).select_related('employee__user').order_by('-check_in_time')[:10]

    # ── Recent activity ───────────────────────────────────────────────────────
    recent_activity = ActivityLog.objects.select_related('user').order_by('-created_at')[:8]

    # ── Per-employee call summary (top 5) ─────────────────────────────────────
    top_callers = CallLog.objects.filter(
        started_at__date__gte=start, started_at__date__lte=end
    ).values(
        'employee__first_name', 'employee__last_name', 'employee__id'
    ).annotate(
        call_count=Count('id')
    ).order_by('-call_count')[:5]

    # ── Chart data: calls per day (last 7 days) ───────────────────────────────
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%b %d'))
        chart_data.append(
            CallLog.objects.filter(started_at__date=d).count()
        )

    context = {
        'page_title': 'Admin Dashboard',
        'total_employees': total_employees,
        'calling_count': calling_count,
        'marketing_count': marketing_count,
        'developer_count': developer_count,
        'total_leads': total_leads,
        'interested': interested,
        'not_interested': not_interested,
        'pending_leads': pending_leads,
        'calls_today': calls_in_selected_range,
        'calls_completed': calls_completed,
        'calls_pending': calls_pending,
        'followups_today': followups_today,
        'overdue_followups': overdue_followups,
        'conversion_rate': conversion_rate,
        'today_attendance': today_attendance,
        'recent_activity': recent_activity,
        'top_callers': top_callers,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'date_range': date_range,
        'start': start,
        'end': end,
        'today': today,
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
def calling_dashboard(request):
    from apps.leads.models import Lead, LeadStatus
    from apps.calling.models import CallLog, FollowUp

    today = date.today()
    user = request.user

    my_leads = Lead.objects.filter(assigned_to=user)
    my_calls_today = CallLog.objects.filter(employee=user, started_at__date=today)
    pending = my_leads.filter(status=LeadStatus.PENDING).count()
    completed_today = my_calls_today.filter(
        result__in=['COMPLETED', 'INTERESTED', 'NOT_INTERESTED']
    ).count()
    interested = my_leads.filter(status=LeadStatus.INTERESTED).count()
    not_interested = my_leads.filter(status=LeadStatus.NOT_INTERESTED).count()
    followups = FollowUp.objects.filter(
        assigned_to=user, is_completed=False
    ).order_by('follow_up_date')[:5]
    overdue = FollowUp.objects.filter(
        assigned_to=user, follow_up_date__lt=today, is_completed=False
    ).count()

    recent_leads = my_leads.select_related('assigned_to').order_by('-updated_at')[:10]

    context = {
        'page_title': 'My Dashboard',
        'total_my_leads': my_leads.count(),
        'pending': pending,
        'completed_today': completed_today,
        'interested': interested,
        'not_interested': not_interested,
        'followups': followups,
        'overdue': overdue,
        'recent_leads': recent_leads,
        'today': today,
    }
    return render(request, 'dashboard/calling.html', context)


@login_required
def marketing_dashboard(request):
    from apps.attendance.models import Attendance
    from apps.locations.models import LocationRecord

    today = date.today()
    user = request.user

    today_attendance = Attendance.objects.filter(employee__user=user, date=today).first()
    this_month_attendance = Attendance.objects.filter(
        employee__user=user,
        date__year=today.year,
        date__month=today.month
    ).count()

    last_location = LocationRecord.objects.filter(
        employee__user=user
    ).order_by('-timestamp').first()

    context = {
        'page_title': 'Marketing Dashboard',
        'today_attendance': today_attendance,
        'this_month_attendance': this_month_attendance,
        'last_location': last_location,
        'today': today,
    }
    return render(request, 'dashboard/marketing.html', context)


@login_required
def developer_dashboard(request):
    from apps.developers.models import Task, TaskStatus, Project

    today = date.today()
    user = request.user

    my_tasks = Task.objects.filter(developer=user)
    pending = my_tasks.filter(status=TaskStatus.PENDING).count()
    in_progress = my_tasks.filter(status=TaskStatus.IN_PROGRESS).count()
    completed = my_tasks.filter(status=TaskStatus.COMPLETED).count()
    overdue = my_tasks.filter(
        due_date__lt=today,
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ).count()

    recent_tasks = my_tasks.select_related('project').order_by('-updated_at')[:8]
    projects = Project.objects.filter(
        tasks__developer=user
    ).distinct()[:5]

    context = {
        'page_title': 'Developer Dashboard',
        'total_tasks': my_tasks.count(),
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'overdue': overdue,
        'recent_tasks': recent_tasks,
        'projects': projects,
        'today': today,
    }
    return render(request, 'dashboard/developer.html', context)
