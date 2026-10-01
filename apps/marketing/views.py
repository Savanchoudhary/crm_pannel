"""
Marketing views.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.core.paginator import Paginator
from datetime import date

from apps.accounts.permissions import marketing_required, admin_required
from apps.accounts.models import User, Role
from .models import MarketingActivity, Campaign, ActivityType, ActivityStatus


@marketing_required
def marketing_home(request):
    user = request.user
    today = date.today()

    my_activities = MarketingActivity.objects.filter(employee=user)
    stats = {
        'total': my_activities.count(),
        'today': my_activities.filter(date=today).count(),
        'this_month': my_activities.filter(
            date__year=today.year, date__month=today.month
        ).count(),
        'leads_generated': my_activities.aggregate(total=Sum('leads_generated'))['total'] or 0,
    }

    recent = my_activities.order_by('-date')[:10]
    from apps.attendance.models import Attendance
    today_attendance = Attendance.objects.filter(employee__user=user, date=today).first()

    return render(request, 'marketing/home.html', {
        'stats': stats,
        'recent_activities': recent,
        'today_attendance': today_attendance,
        'today': today,
    })


@marketing_required
def activity_list(request):
    user = request.user
    if user.is_admin:
        qs = MarketingActivity.objects.select_related('employee')
    else:
        qs = MarketingActivity.objects.filter(employee=user)

    search = request.GET.get('q', '')
    if search:
        qs = qs.filter(title__icontains=search)

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    date_filter = request.GET.get('date', '')
    if date_filter:
        qs = qs.filter(date=date_filter)

    qs = qs.order_by('-date')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'marketing/activities.html', {
        'activities': page,
        'status_choices': ActivityStatus.choices,
        'type_choices': ActivityType.choices,
        'status_filter': status_filter,
        'search': search,
    })


@marketing_required
def activity_create(request):
    if request.method == 'POST':
        data = request.POST
        activity = MarketingActivity.objects.create(
            employee=request.user,
            activity_type=data.get('activity_type', 'OTHER'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            location=data.get('location', ''),
            date=data.get('date'),
            start_time=data.get('start_time') or None,
            end_time=data.get('end_time') or None,
            contacts_met=data.get('contacts_met', 0),
            leads_generated=data.get('leads_generated', 0),
            notes=data.get('notes', ''),
        )
        messages.success(request, 'Activity logged successfully.')
        return redirect('marketing:activities')

    return render(request, 'marketing/activity_form.html', {
        'type_choices': ActivityType.choices,
        'today': date.today(),
    })
