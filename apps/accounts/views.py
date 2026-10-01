"""
Accounts views — Login, Logout, Employee CRUD, Profile, Password management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import User, EmployeeProfile, Department, ActivityLog, Role
from .forms import (
    LoginForm, EmployeeCreateForm, EmployeeEditForm,
    EmployeeProfileForm, AdminPasswordResetForm, ProfileEditForm, DepartmentForm
)
from .permissions import admin_required


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            remember = form.cleaned_data.get('remember_me')
            if not remember:
                request.session.set_expiry(0)
            login(request, user)
            # Log activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityLog.ActionType.LOGIN,
                description=f'{user.full_name} logged in.',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            messages.success(request, f'Welcome back, {user.first_name}!')
            next_url = request.GET.get('next', 'dashboard:index')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    ActivityLog.objects.create(
        user=request.user,
        action=ActivityLog.ActionType.LOGOUT,
        description=f'{request.user.full_name} logged out.',
        ip_address=get_client_ip(request),
    )
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@login_required
def profile_view(request):
    user = request.user
    try:
        profile = user.profile
    except EmployeeProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=user)

    # Recent activity
    activity = ActivityLog.objects.filter(user=user).order_by('-created_at')[:10]
    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
        'activity': activity,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        user = request.user
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)
            ActivityLog.objects.create(
                user=user,
                action=ActivityLog.ActionType.UPDATE,
                description='Password changed.',
                ip_address=get_client_ip(request),
            )
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:profile')

    return render(request, 'accounts/change_password.html')


# ---------------------------------------------------------------------------
# Employee Management (Admin only)
# ---------------------------------------------------------------------------
@admin_required
def employee_list(request):
    qs = User.objects.select_related('profile__department').order_by('first_name', 'last_name')

    # Search
    search = request.GET.get('search', '')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__employee_id__icontains=search)
        )

    # Filters
    role_filter = request.GET.get('role', '')
    if role_filter:
        qs = qs.filter(role=role_filter)

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    dept_filter = request.GET.get('department', '')
    if dept_filter:
        qs = qs.filter(profile__department_id=dept_filter)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    departments = list(Department.objects.filter(is_active=True))
    for department in departments:
        department.is_selected = str(department.id) == dept_filter
    stats = {
        'total': User.objects.filter(is_superuser=False).count(),
        'active': User.objects.filter(is_active=True, is_superuser=False).count(),
        'calling': User.objects.filter(role=Role.CALLING).count(),
        'marketing': User.objects.filter(role=Role.MARKETING).count(),
        'developers': User.objects.filter(role=Role.DEVELOPER).count(),
    }

    return render(request, 'employees/list.html', {
        'employees': page,
        'departments': departments,
        'stats': stats,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
        'role_choices': [
            (value, label, role_filter == value)
            for value, label in Role.choices
        ],
        'status_active': status_filter == 'active',
        'status_inactive': status_filter == 'inactive',
    })


@admin_required
def employee_create(request):
    user_form = EmployeeCreateForm(request.POST or None, request.FILES or None)
    profile_form = EmployeeProfileForm(request.POST or None)
    departments = Department.objects.filter(is_active=True)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    user = user_form.save()
                    profile_form = EmployeeProfileForm(
                        request.POST,
                        instance=EmployeeProfile.objects.get(user=user),
                    )
                    profile_form.is_valid()
                    profile_form.save()
            except IntegrityError as error:
                if 'accounts_user.email' in str(error):
                    user_form.add_error('email', 'An account with this email already exists.')
                else:
                    raise
            else:
                ActivityLog.objects.create(
                    user=request.user,
                    action=ActivityLog.ActionType.CREATE,
                    model_name='User',
                    object_id=str(user.id),
                    description=f'Created employee: {user.full_name}',
                    ip_address=get_client_ip(request),
                )
                messages.success(request, f'Employee {user.full_name} created successfully.')
                return redirect('accounts:employee_list')

        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'employees/create.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'departments': departments,
    })


@admin_required
def employee_detail(request, pk):
    employee = get_object_or_404(User, pk=pk)
    try:
        profile = employee.profile
    except EmployeeProfile.DoesNotExist:
        profile = None

    activity = ActivityLog.objects.filter(user=employee).order_by('-created_at')[:20]
    return render(request, 'employees/detail.html', {
        'employee': employee,
        'profile': profile,
        'activity': activity,
    })


@admin_required
def employee_edit(request, pk):
    employee = get_object_or_404(User, pk=pk)
    try:
        profile = employee.profile
    except EmployeeProfile.DoesNotExist:
        profile = EmployeeProfile(user=employee)

    user_form = EmployeeEditForm(request.POST or None, request.FILES or None, instance=employee)
    profile_form = EmployeeProfileForm(request.POST or None, instance=profile)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            p = profile_form.save(commit=False)
            p.user = employee
            p.save()

            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ActionType.UPDATE,
                model_name='User',
                object_id=str(employee.id),
                description=f'Updated employee: {employee.full_name}',
                ip_address=get_client_ip(request),
            )
            messages.success(request, 'Employee updated successfully.')
            return redirect('accounts:employee_detail', pk=pk)
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'employees/edit.html', {
        'employee': employee,
        'user_form': user_form,
        'profile_form': profile_form,
    })


@admin_required
@require_POST
def employee_toggle_status(request, pk):
    employee = get_object_or_404(User, pk=pk)
    if employee == request.user:
        return JsonResponse({'error': 'Cannot deactivate yourself.'}, status=400)

    employee.is_active = not employee.is_active
    employee.save(update_fields=['is_active'])

    action = 'activated' if employee.is_active else 'deactivated'
    ActivityLog.objects.create(
        user=request.user,
        action=ActivityLog.ActionType.UPDATE,
        model_name='User',
        object_id=str(employee.id),
        description=f'Employee {employee.full_name} {action}.',
        ip_address=get_client_ip(request),
    )
    messages.success(request, f'Employee {action} successfully.')
    return JsonResponse({'status': 'active' if employee.is_active else 'inactive'})


@admin_required
@require_POST
def employee_delete(request, pk):
    employee = get_object_or_404(User, pk=pk)
    if employee == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:employee_list')
    if employee.is_superuser:
        messages.error(request, 'Superuser accounts cannot be deleted here.')
        return redirect('accounts:employee_list')

    employee_name = employee.full_name
    employee_id = str(employee.id)
    ActivityLog.objects.create(
        user=request.user,
        action=ActivityLog.ActionType.DELETE,
        model_name='User',
        object_id=employee_id,
        description=f'Deleted employee: {employee_name}',
        ip_address=get_client_ip(request),
    )
    employee.delete()
    messages.success(request, f'Employee {employee_name} deleted successfully.')
    return redirect('accounts:employee_list')


@admin_required
def employee_reset_password(request, pk):
    employee = get_object_or_404(User, pk=pk)
    form = AdminPasswordResetForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        employee.set_password(form.cleaned_data['new_password1'])
        employee.save()
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.UPDATE,
            model_name='User',
            object_id=str(employee.id),
            description=f'Password reset for employee: {employee.full_name}',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'Password reset for {employee.full_name}.')
        return redirect('accounts:employee_detail', pk=pk)

    return render(request, 'employees/reset_password.html', {
        'employee': employee,
        'form': form,
    })


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------
@admin_required
def department_list(request):
    departments = Department.objects.annotate(
        emp_count=Count('employees')
    ).order_by('name')
    return render(request, 'employees/departments.html', {'departments': departments})


@admin_required
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        dept = form.save()
        messages.success(request, f'Department "{dept.name}" created.')
        return redirect('accounts:department_list')
    return render(request, 'employees/department_form.html', {'form': form, 'action': 'Create'})


@admin_required
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Department "{dept.name}" updated.')
        return redirect('accounts:department_list')
    return render(request, 'employees/department_form.html', {'form': form, 'action': 'Edit'})


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------
@admin_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').order_by('-created_at')

    user_filter = request.GET.get('user', '')
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get('page'))

    users = User.objects.filter(is_active=True).order_by('first_name')
    return render(request, 'employees/activity_log.html', {
        'logs': page,
        'users': users,
        'action_choices': ActivityLog.ActionType.choices,
        'user_filter': user_filter,
        'action_filter': action_filter,
    })


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
