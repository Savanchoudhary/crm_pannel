"""
Calling views — call logging, follow-ups, call monitoring.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date, timedelta

from apps.accounts.permissions import calling_required, admin_required
from apps.accounts.models import User, Role, ActivityLog
from apps.accounts.views import get_client_ip
from apps.leads.models import Lead, LeadStatus
from .models import CallLog, FollowUp, CallResult


# ---------------------------------------------------------------------------
# Start Call
# ---------------------------------------------------------------------------
@login_required
@require_POST
def start_call(request, lead_pk):
    lead = get_object_or_404(Lead, pk=lead_pk)
    user = request.user

    if not user.is_admin and lead.assigned_to != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    # Check for already active call on this lead
    active_call = CallLog.objects.filter(lead=lead, result=CallResult.CALLING).first()
    if active_call:
        return JsonResponse({'error': 'A call is already active for this lead.', 'call_id': active_call.id})

    call = CallLog.objects.create(
        lead=lead,
        employee=user,
        started_at=timezone.now(),
        result=CallResult.CALLING,
    )

    # Update lead status
    lead.status = LeadStatus.CALLING
    lead.last_called_at = timezone.now()
    lead.save(update_fields=['status', 'last_called_at', 'updated_at'])

    return JsonResponse({
        'call_id': call.id,
        'started_at': call.started_at.isoformat(),
        'message': 'Call started. Log the result when done.',
    })


# ---------------------------------------------------------------------------
# End Call
# ---------------------------------------------------------------------------
@login_required
@require_POST
def end_call(request, call_pk):
    call = get_object_or_404(CallLog, pk=call_pk)
    user = request.user

    if not user.is_admin and call.employee != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    result = request.POST.get('result', CallResult.COMPLETED)
    notes = request.POST.get('notes', '')
    follow_up_date = request.POST.get('follow_up_date', '')

    call.ended_at = timezone.now()
    call.result = result
    call.notes = notes

    # Interested flag
    if result == CallResult.INTERESTED:
        call.is_interested = True
    elif result == CallResult.NOT_INTERESTED:
        call.is_interested = False

    # Follow-up
    if result == CallResult.FOLLOW_UP and follow_up_date:
        call.follow_up_required = True
        call.follow_up_date = follow_up_date
        # Create FollowUp record
        FollowUp.objects.create(
            lead=call.lead,
            call_log=call,
            assigned_to=call.employee,
            created_by=user,
            follow_up_date=follow_up_date,
            notes=notes,
        )
        # Notify
        try:
            from apps.notifications.models import Notification
            Notification.objects.create(
                recipient=call.employee,
                title='Follow-up Scheduled',
                message=f'Follow-up for "{call.lead.name}" scheduled on {follow_up_date}.',
                notification_type='FOLLOW_UP',
                related_object_id=call.lead.id,
            )
        except Exception:
            pass

    call.save()  # triggers duration calculation via save()

    # Update lead status
    status_map = {
        CallResult.INTERESTED: LeadStatus.INTERESTED,
        CallResult.NOT_INTERESTED: LeadStatus.NOT_INTERESTED,
        CallResult.FOLLOW_UP: LeadStatus.FOLLOW_UP,
        CallResult.NO_ANSWER: LeadStatus.NO_ANSWER,
        CallResult.BUSY: LeadStatus.BUSY,
        CallResult.COMPLETED: LeadStatus.COMPLETED,
    }
    new_lead_status = status_map.get(result, LeadStatus.COMPLETED)
    call.lead.status = new_lead_status
    call.lead.save(update_fields=['status', 'updated_at'])

    return JsonResponse({
        'duration': call.duration_display,
        'duration_seconds': call.duration_seconds,
        'result': call.result,
        'lead_status': new_lead_status,
    })


# ---------------------------------------------------------------------------
# Calling Dashboard (employee view)
# ---------------------------------------------------------------------------
@calling_required
def calling_home(request):
    user = request.user
    today = date.today()

    my_leads = Lead.objects.filter(assigned_to=user)
    today_calls = CallLog.objects.filter(employee=user, started_at__date=today)

    stats = {
        'total_leads': my_leads.count(),
        'pending': my_leads.filter(status=LeadStatus.PENDING).count(),
        'completed_today': today_calls.exclude(result=CallResult.CALLING).count(),
        'interested': my_leads.filter(status=LeadStatus.INTERESTED).count(),
        'not_interested': my_leads.filter(status=LeadStatus.NOT_INTERESTED).count(),
        'follow_up': my_leads.filter(status=LeadStatus.FOLLOW_UP).count(),
        'overdue_followups': FollowUp.objects.filter(
            assigned_to=user, follow_up_date__lt=today, is_completed=False
        ).count(),
    }

    # Today's follow-ups
    todays_followups = FollowUp.objects.filter(
        assigned_to=user, follow_up_date=today, is_completed=False
    ).select_related('lead')[:5]

    # Recent leads
    recent_leads = my_leads.select_related('assigned_to').order_by('-updated_at')[:10]

    # Overdue follow-ups
    overdue = FollowUp.objects.filter(
        assigned_to=user, follow_up_date__lt=today, is_completed=False
    ).select_related('lead').order_by('follow_up_date')[:5]

    return render(request, 'calling/home.html', {
        **stats,
        'todays_followups': todays_followups,
        'recent_leads': recent_leads,
        'overdue': overdue,
        'today': today,
    })


# ---------------------------------------------------------------------------
# Admin Call Monitor
# ---------------------------------------------------------------------------
@admin_required
def call_monitor(request):
    today = date.today()

    qs = CallLog.objects.select_related('lead', 'employee').order_by('-started_at')

    # Filters
    employee_filter = request.GET.get('employee', '')
    if employee_filter:
        qs = qs.filter(employee_id=employee_filter)

    date_from = request.GET.get('date_from', str(today))
    date_to = request.GET.get('date_to', str(today))
    if date_from:
        qs = qs.filter(started_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(started_at__date__lte=date_to)

    result_filter = request.GET.get('result', '')
    if result_filter:
        qs = qs.filter(result=result_filter)

    interest_filter = request.GET.get('interest', '')
    if interest_filter == 'yes':
        qs = qs.filter(is_interested=True)
    elif interest_filter == 'no':
        qs = qs.filter(is_interested=False)

    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page'))

    # Summary stats
    stats = {
        'total': qs.count(),
        'interested': qs.filter(result=CallResult.INTERESTED).count(),
        'not_interested': qs.filter(result=CallResult.NOT_INTERESTED).count(),
        'no_answer': qs.filter(result=CallResult.NO_ANSWER).count(),
        'follow_up': qs.filter(result=CallResult.FOLLOW_UP).count(),
        'total_duration': qs.aggregate(total=Sum('duration_seconds'))['total'] or 0,
    }

    calling_employees = User.objects.filter(role=Role.CALLING, is_active=True)

    return render(request, 'calling/monitor.html', {
        'calls': page,
        'stats': stats,
        'calling_employees': calling_employees,
        'result_choices': CallResult.choices,
        'employee_filter': employee_filter,
        'date_from': date_from,
        'date_to': date_to,
        'result_filter': result_filter,
        'interest_filter': interest_filter,
    })


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------
@login_required
def followup_list(request):
    user = request.user
    today = date.today()

    if user.is_admin:
        qs = FollowUp.objects.select_related('lead', 'assigned_to')
    else:
        qs = FollowUp.objects.filter(assigned_to=user).select_related('lead')

    # Filters
    status_filter = request.GET.get('status', 'pending')
    if status_filter == 'pending':
        qs = qs.filter(is_completed=False, follow_up_date__gte=today)
    elif status_filter == 'overdue':
        qs = qs.filter(is_completed=False, follow_up_date__lt=today)
    elif status_filter == 'completed':
        qs = qs.filter(is_completed=True)
    elif status_filter == 'today':
        qs = qs.filter(is_completed=False, follow_up_date=today)

    date_filter = request.GET.get('date', '')
    if date_filter:
        qs = qs.filter(follow_up_date=date_filter)

    qs = qs.order_by('follow_up_date')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    stats = {
        'today': FollowUp.objects.filter(
            **({} if user.is_admin else {'assigned_to': user}),
            follow_up_date=today, is_completed=False
        ).count(),
        'overdue': FollowUp.objects.filter(
            **({} if user.is_admin else {'assigned_to': user}),
            follow_up_date__lt=today, is_completed=False
        ).count(),
        'pending': FollowUp.objects.filter(
            **({} if user.is_admin else {'assigned_to': user}),
            follow_up_date__gte=today, is_completed=False
        ).count(),
    }

    return render(request, 'calling/followups.html', {
        'followups': page,
        'stats': stats,
        'status_filter': status_filter,
        'today': today,
    })


@login_required
@require_POST
def complete_followup(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    user = request.user

    if not user.is_admin and followup.assigned_to != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    followup.is_completed = True
    followup.completed_at = timezone.now()
    followup.completed_notes = request.POST.get('notes', '')
    followup.save()

    return JsonResponse({'status': 'completed'})
