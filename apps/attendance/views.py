"""
Attendance views — check-in, check-out, history, admin report.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse
from urllib.parse import urlencode
from django.db.models import Count, Avg
from django.core.paginator import Paginator
from datetime import date

from apps.accounts.models import EmployeeProfile, User, Role
from apps.accounts.permissions import admin_required
from .models import (
    Attendance, AttendanceStatus, Student, StudentAttendance,
    StudentAttendanceStatus, StudentTechnology,
)


@login_required
@require_POST
def check_in(request):
    user = request.user
    today = date.today()

    try:
        profile = user.profile
    except EmployeeProfile.DoesNotExist:
        return JsonResponse({'error': 'Employee profile not found.'}, status=400)

    existing = Attendance.objects.filter(employee=profile, date=today).first()
    if existing and existing.check_in_time:
        return JsonResponse({'error': 'Already checked in today.'}, status=400)

    lat = request.POST.get('lat')
    lng = request.POST.get('lng')
    location_name = request.POST.get('location_name', '')

    attendance, created = Attendance.objects.get_or_create(
        employee=profile,
        date=today,
        defaults={'status': AttendanceStatus.PRESENT}
    )
    attendance.check_in_time = timezone.now()
    attendance.check_in_location = location_name
    if lat:
        attendance.check_in_lat = float(lat)
    if lng:
        attendance.check_in_lng = float(lng)
    attendance.save()

    return JsonResponse({
        'status': 'checked_in',
        'time': attendance.check_in_time.strftime('%H:%M:%S'),
        'message': f'Checked in at {attendance.check_in_time.strftime("%H:%M")}',
    })


@login_required
@require_POST
def check_out(request):
    user = request.user
    today = date.today()

    try:
        profile = user.profile
        attendance = Attendance.objects.get(employee=profile, date=today)
    except (EmployeeProfile.DoesNotExist, Attendance.DoesNotExist):
        return JsonResponse({'error': 'No check-in record found for today.'}, status=400)

    if not attendance.check_in_time:
        return JsonResponse({'error': 'You have not checked in today.'}, status=400)
    if attendance.check_out_time:
        return JsonResponse({'error': 'Already checked out today.'}, status=400)

    lat = request.POST.get('lat')
    lng = request.POST.get('lng')
    location_name = request.POST.get('location_name', '')

    attendance.check_out_time = timezone.now()
    attendance.check_out_location = location_name
    if lat:
        attendance.check_out_lat = float(lat)
    if lng:
        attendance.check_out_lng = float(lng)
    attendance.save()  # triggers working_hours calculation

    return JsonResponse({
        'status': 'checked_out',
        'time': attendance.check_out_time.strftime('%H:%M:%S'),
        'working_hours': str(attendance.working_hours),
        'working_hours_display': attendance.working_hours_display,
        'message': f'Checked out at {attendance.check_out_time.strftime("%H:%M")}. Total: {attendance.working_hours_display}',
    })


@login_required
def my_attendance(request):
    user = request.user
    today = date.today()

    try:
        profile = user.profile
    except EmployeeProfile.DoesNotExist:
        messages.error(request, 'Employee profile not found.')
        return redirect('dashboard:index')

    today_record = Attendance.objects.filter(employee=profile, date=today).first()

    # This month
    records = Attendance.objects.filter(
        employee=profile,
        date__year=today.year,
        date__month=today.month
    ).order_by('-date')

    total_days = records.count()
    present_days = records.filter(status=AttendanceStatus.PRESENT).count()
    total_hours = sum(float(r.working_hours) for r in records)

    # All history
    paginator = Paginator(Attendance.objects.filter(employee=profile).order_by('-date'), 30)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'attendance/my_attendance.html', {
        'today_record': today_record,
        'records': page,
        'total_days': total_days,
        'present_days': present_days,
        'total_hours': round(total_hours, 2),
        'today': today,
    })


@admin_required
def attendance_report(request):
    today = date.today()
    qs = Attendance.objects.select_related('employee__user').order_by('-date')

    # Filters
    emp_filter = request.GET.get('employee', '')
    if emp_filter:
        qs = qs.filter(employee_id=emp_filter)

    date_from = request.GET.get('date_from', str(today.replace(day=1)))
    date_to = request.GET.get('date_to', str(today))
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    # Today's summary
    today_records = Attendance.objects.filter(date=today).select_related('employee__user')
    today_checkins = today_records.filter(check_in_time__isnull=False).count()

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    employees = EmployeeProfile.objects.select_related('user').filter(user__is_active=True)

    return render(request, 'attendance/report.html', {
        'records': page,
        'employees': employees,
        'emp_filter': emp_filter,
        'date_from': date_from,
        'date_to': date_to,
        'today': today,
        'today_records': today_records,
        'today_checkins': today_checkins,
    })


@login_required
def attendance_status(request):
    """API: Return today's attendance status for the current user."""
    user = request.user
    today = date.today()
    try:
        profile = user.profile
        record = Attendance.objects.filter(employee=profile, date=today).first()
        if record:
            return JsonResponse({
                'is_checked_in': record.is_checked_in,
                'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                'working_hours': record.working_hours_display,
            })
        return JsonResponse({'is_checked_in': False, 'check_in_time': None, 'check_out_time': None})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def student_attendance(request):
    if not request.user.is_developer:
        raise PermissionDenied

    today = timezone.localdate()
    selected_date = parse_date(request.POST.get('date', '') if request.method == 'POST' else request.GET.get('date', '')) or today
    technology_filter = request.POST.get('technology', '') if request.method == 'POST' else request.GET.get('technology', '')
    valid_technologies = {value for value, _ in StudentTechnology.choices}
    if technology_filter not in valid_technologies:
        technology_filter = ''

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_student':
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            technology = request.POST.get('new_student_technology', '')
            if not name or technology not in valid_technologies:
                messages.error(request, 'Enter a student name and select a technology.')
            else:
                Student.objects.create(name=name, phone=phone, technology=technology)
                messages.success(request, f'Student {name} added.')
        elif action == 'mark_attendance':
            valid_statuses = {value for value, _ in StudentAttendanceStatus.choices}
            students_to_mark = Student.objects.filter(is_active=True)
            if technology_filter:
                students_to_mark = students_to_mark.filter(technology=technology_filter)
            marked_count = 0
            for student in students_to_mark:
                status = request.POST.get(f'status_{student.pk}', '')
                if status in valid_statuses:
                    StudentAttendance.objects.update_or_create(
                        student=student,
                        date=selected_date,
                        defaults={'status': status, 'marked_by': request.user},
                    )
                    marked_count += 1
            messages.success(request, f'Attendance saved for {marked_count} student(s).')

        query = urlencode({'date': selected_date.isoformat(), 'technology': technology_filter})
        return redirect(f'{reverse("attendance:student_attendance")}?{query}')

    students = Student.objects.filter(is_active=True)
    if technology_filter:
        students = students.filter(technology=technology_filter)
    attendance_by_student = {
        record.student_id: record
        for record in StudentAttendance.objects.filter(
            student__in=students, date=selected_date
        )
    }

    return render(request, 'attendance/student_attendance.html', {
        'students': students,
        'attendance_by_student': attendance_by_student,
        'selected_date': selected_date,
        'technology_filter': technology_filter,
        'technology_choices': StudentTechnology.choices,
        'status_choices': StudentAttendanceStatus.choices,
    })
