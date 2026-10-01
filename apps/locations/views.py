"""
Location views — tracking (consent-based), history, admin map view.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import date

from apps.accounts.models import User, Role
from apps.accounts.permissions import admin_required
from .models import LocationRecord, TrackingSession


# ---------------------------------------------------------------------------
# Employee: Start / Stop Tracking (consent-based)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def start_tracking(request):
    """Employee explicitly starts location tracking."""
    user = request.user
    # End any existing active session
    TrackingSession.objects.filter(employee=user, is_active=True).update(
        is_active=False, ended_at=timezone.now()
    )
    session = TrackingSession.objects.create(employee=user)
    return JsonResponse({
        'session_id': session.id,
        'started_at': session.started_at.isoformat(),
        'message': 'Location tracking started. Your location is being recorded.',
    })


@login_required
@require_POST
def stop_tracking(request):
    """Employee explicitly stops location tracking."""
    user = request.user
    sessions = TrackingSession.objects.filter(employee=user, is_active=True)
    sessions.update(is_active=False, ended_at=timezone.now())
    return JsonResponse({'message': 'Location tracking stopped.'})


@login_required
def tracking_status(request):
    """Check if employee has an active tracking session."""
    user = request.user
    active = TrackingSession.objects.filter(employee=user, is_active=True).first()
    last_loc = LocationRecord.objects.filter(employee=user).order_by('-timestamp').first()
    return JsonResponse({
        'is_tracking': active is not None,
        'session_id': active.id if active else None,
        'started_at': active.started_at.isoformat() if active else None,
        'last_location': {
            'lat': last_loc.latitude,
            'lng': last_loc.longitude,
            'timestamp': last_loc.timestamp.isoformat(),
            'accuracy': last_loc.accuracy,
        } if last_loc else None,
    })


# ---------------------------------------------------------------------------
# Record location update (from JS Geolocation API)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def record_location(request):
    """
    Receive a location update from the browser.
    Only records if there is an active tracking session.
    """
    user = request.user
    active_session = TrackingSession.objects.filter(employee=user, is_active=True).first()
    if not active_session:
        return JsonResponse({'error': 'No active tracking session. Start tracking first.'}, status=400)

    try:
        lat = float(request.POST.get('latitude'))
        lng = float(request.POST.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid coordinates.'}, status=400)

    accuracy = request.POST.get('accuracy')
    altitude = request.POST.get('altitude')

    LocationRecord.objects.create(
        employee=user,
        session=active_session,
        latitude=lat,
        longitude=lng,
        accuracy=float(accuracy) if accuracy else None,
        altitude=float(altitude) if altitude else None,
        address=request.POST.get('address', ''),
        timestamp=timezone.now(),
    )
    return JsonResponse({'status': 'recorded'})


# ---------------------------------------------------------------------------
# Employee: Location history
# ---------------------------------------------------------------------------
@login_required
def my_location_history(request):
    user = request.user
    today = date.today()

    date_filter = request.GET.get('date', str(today))
    records = LocationRecord.objects.filter(
        employee=user,
        timestamp__date=date_filter,
    ).order_by('timestamp')

    sessions = TrackingSession.objects.filter(
        employee=user,
        started_at__date=date_filter,
    ).order_by('-started_at')

    return render(request, 'locations/my_history.html', {
        'records': records,
        'sessions': sessions,
        'date_filter': date_filter,
        'today': today,
    })


# ---------------------------------------------------------------------------
# Admin: View all employee locations
# ---------------------------------------------------------------------------
@admin_required
def admin_location_map(request):
    """Show current (last known) locations of all tracked employees."""
    # Get employees who have tracking sessions
    tracked_employees = User.objects.filter(
        role__in=[Role.CALLING, Role.MARKETING],
        is_active=True
    )

    # Get last known location for each
    employee_locations = []
    for emp in tracked_employees:
        last_loc = LocationRecord.objects.filter(employee=emp).order_by('-timestamp').first()
        active_session = TrackingSession.objects.filter(employee=emp, is_active=True).first()
        if last_loc:
            employee_locations.append({
                'id': emp.id,
                'name': emp.full_name,
                'role': emp.get_role_display(),
                'lat': last_loc.latitude,
                'lng': last_loc.longitude,
                'timestamp': last_loc.timestamp.strftime('%Y-%m-%d %H:%M'),
                'is_tracking': active_session is not None,
                'accuracy': last_loc.accuracy,
            })

    return render(request, 'locations/admin_map.html', {
        'employee_locations': employee_locations,
        'tracked_employees': tracked_employees,
    })


@admin_required
def admin_location_history(request):
    """Admin views location history for a specific employee on a date."""
    today = date.today()
    employee_id = request.GET.get('employee', '')
    date_filter = request.GET.get('date', str(today))

    records = []
    selected_employee = None

    if employee_id:
        try:
            selected_employee = User.objects.get(pk=employee_id)
            records = LocationRecord.objects.filter(
                employee=selected_employee,
                timestamp__date=date_filter,
            ).order_by('timestamp')
        except User.DoesNotExist:
            pass

    employees = User.objects.filter(
        role__in=[Role.CALLING, Role.MARKETING], is_active=True
    )

    return render(request, 'locations/admin_history.html', {
        'records': records,
        'selected_employee': selected_employee,
        'employees': employees,
        'employee_id': employee_id,
        'date_filter': date_filter,
        'today': today,
    })
