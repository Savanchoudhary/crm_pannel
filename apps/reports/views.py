"""
Reports views — calling, marketing, developers, attendance.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.http import HttpResponse
from datetime import date, timedelta
import json

from apps.accounts.permissions import admin_required
from apps.accounts.models import User, Role
from apps.leads.models import Lead, LeadStatus
from apps.calling.models import CallLog, FollowUp, CallResult
from apps.attendance.models import Attendance
from apps.developers.models import Task, TaskStatus


@admin_required
def reports_home(request):
    return render(request, 'reports/home.html')


@admin_required
def calling_report(request):
    today = date.today()

    # Date range
    date_from = request.GET.get('date_from', str(today - timedelta(days=29)))
    date_to = request.GET.get('date_to', str(today))

    calls = CallLog.objects.filter(
        started_at__date__gte=date_from,
        started_at__date__lte=date_to,
    )

    # Per employee
    per_employee = calls.values(
        'employee__first_name', 'employee__last_name', 'employee__id'
    ).annotate(
        total=Count('id'),
        interested=Count('id', filter=Q(result=CallResult.INTERESTED)),
        not_interested=Count('id', filter=Q(result=CallResult.NOT_INTERESTED)),
        no_answer=Count('id', filter=Q(result=CallResult.NO_ANSWER)),
        follow_up=Count('id', filter=Q(result=CallResult.FOLLOW_UP)),
        total_duration=Sum('duration_seconds'),
    ).order_by('-total')

    # Per day (for chart)
    from collections import defaultdict
    daily = defaultdict(int)
    for call in calls.values('started_at__date').annotate(count=Count('id')):
        daily[str(call['started_at__date'])] = call['count']

    # Build chart data for last N days
    days = []
    chart_data = []
    current = date.fromisoformat(date_from) if date_from else today - timedelta(days=29)
    end = date.fromisoformat(date_to) if date_to else today
    while current <= end:
        days.append(current.strftime('%b %d'))
        chart_data.append(daily.get(str(current), 0))
        current += timedelta(days=1)

    # Summary
    total_calls = calls.count()
    total_interested = calls.filter(result=CallResult.INTERESTED).count()
    total_duration = calls.aggregate(t=Sum('duration_seconds'))['t'] or 0
    avg_duration = calls.aggregate(a=Avg('duration_seconds'))['a'] or 0
    conversion_rate = round((total_interested / total_calls * 100), 1) if total_calls else 0

    return render(request, 'reports/calling.html', {
        'per_employee': per_employee,
        'chart_labels': json.dumps(days),
        'chart_data': json.dumps(chart_data),
        'total_calls': total_calls,
        'total_interested': total_interested,
        'total_duration': total_duration,
        'avg_duration': int(avg_duration),
        'conversion_rate': conversion_rate,
        'date_from': date_from,
        'date_to': date_to,
    })


@admin_required
def attendance_report_view(request):
    today = date.today()
    date_from = request.GET.get('date_from', str(today.replace(day=1)))
    date_to = request.GET.get('date_to', str(today))

    records = Attendance.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).select_related('employee__user')

    per_employee = {}
    for record in records:
        emp_name = record.employee.user.full_name
        if emp_name not in per_employee:
            per_employee[emp_name] = {
                'days': 0,
                'total_hours': 0,
                'check_ins': 0,
            }
        per_employee[emp_name]['days'] += 1
        per_employee[emp_name]['total_hours'] += float(record.working_hours)
        if record.check_in_time:
            per_employee[emp_name]['check_ins'] += 1

    return render(request, 'reports/attendance.html', {
        'per_employee': per_employee.items(),
        'date_from': date_from,
        'date_to': date_to,
        'total_records': records.count(),
    })


@admin_required
def developer_report(request):
    today = date.today()
    tasks = Task.objects.select_related('developer', 'project')

    per_developer = tasks.values(
        'developer__first_name', 'developer__last_name', 'developer__id'
    ).annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status=TaskStatus.COMPLETED)),
        in_progress=Count('id', filter=Q(status=TaskStatus.IN_PROGRESS)),
        pending=Count('id', filter=Q(status=TaskStatus.PENDING)),
        overdue=Count('id', filter=Q(
            due_date__lt=today,
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        )),
        est_hours=Sum('estimated_hours'),
        actual_hours=Sum('actual_hours'),
    ).order_by('-total')

    return render(request, 'reports/developers.html', {
        'per_developer': per_developer,
        'today': today,
    })
