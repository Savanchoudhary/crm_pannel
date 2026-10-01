"""
Developer views — tasks, projects, dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date

from apps.accounts.permissions import developer_required, admin_required
from apps.accounts.models import User, Role, ActivityLog
from apps.accounts.views import get_client_ip
from .models import Task, Project, TaskStatus, TaskPriority


@developer_required
def developer_home(request):
    user = request.user
    today = date.today()

    if user.is_admin:
        my_tasks = Task.objects.select_related('project', 'developer')
    else:
        my_tasks = Task.objects.filter(developer=user).select_related('project')

    stats = {
        'total': my_tasks.count(),
        'pending': my_tasks.filter(status=TaskStatus.PENDING).count(),
        'in_progress': my_tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
        'completed': my_tasks.filter(status=TaskStatus.COMPLETED).count(),
        'overdue': my_tasks.filter(
            due_date__lt=today,
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ).count(),
    }

    recent_tasks = my_tasks.order_by('-updated_at')[:8]
    projects = Project.objects.filter(is_active=True)[:5]

    return render(request, 'developers/home.html', {
        **stats,
        'recent_tasks': recent_tasks,
        'projects': projects,
        'today': today,
    })


@developer_required
def task_list(request):
    user = request.user
    today = date.today()

    if user.is_admin:
        qs = Task.objects.select_related('project', 'developer')
    else:
        qs = Task.objects.filter(developer=user).select_related('project')

    # Search
    search = request.GET.get('q', '')
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    project_filter = request.GET.get('project', '')
    if project_filter:
        qs = qs.filter(project_id=project_filter)

    dev_filter = request.GET.get('developer', '')
    if dev_filter and user.is_admin:
        qs = qs.filter(developer_id=dev_filter)

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    projects = Project.objects.filter(is_active=True)
    developers = User.objects.filter(role=Role.DEVELOPER, is_active=True) if user.is_admin else []

    return render(request, 'developers/tasks.html', {
        'tasks': page,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'projects': projects,
        'developers': developers,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'project_filter': project_filter,
        'dev_filter': dev_filter,
        'search': search,
        'today': today,
    })


@admin_required
def task_create(request):
    if request.method == 'POST':
        data = request.POST
        task = Task.objects.create(
            title=data.get('title'),
            description=data.get('description', ''),
            developer_id=data.get('developer') or None,
            project_id=data.get('project') or None,
            priority=data.get('priority', TaskPriority.MEDIUM),
            status=TaskStatus.PENDING,
            start_date=data.get('start_date') or None,
            due_date=data.get('due_date') or None,
            estimated_hours=data.get('estimated_hours') or 0,
            notes=data.get('notes', ''),
            created_by=request.user,
        )
        # Notify developer
        if task.developer:
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=task.developer,
                    title='New Task Assigned',
                    message=f'Task "{task.title}" has been assigned to you.',
                    notification_type='TASK_ASSIGNED',
                    related_object_id=task.id,
                )
            except Exception:
                pass

        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.CREATE,
            model_name='Task',
            object_id=str(task.id),
            description=f'Created task: {task.title}',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'Task "{task.title}" created.')
        return redirect('developers:tasks')

    projects = Project.objects.filter(is_active=True)
    developers = User.objects.filter(role=Role.DEVELOPER, is_active=True)
    return render(request, 'developers/task_form.html', {
        'projects': projects,
        'developers': developers,
        'priority_choices': TaskPriority.choices,
        'action': 'Create',
    })


@login_required
@require_POST
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    user = request.user

    if not user.is_admin and task.developer != user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    new_status = request.POST.get('status')
    if new_status not in [c[0] for c in TaskStatus.choices]:
        return JsonResponse({'error': 'Invalid status.'}, status=400)

    old_status = task.status
    task.status = new_status
    actual_hours = request.POST.get('actual_hours')
    if actual_hours:
        task.actual_hours = actual_hours

    if new_status == TaskStatus.COMPLETED and not task.completed_date:
        task.completed_date = timezone.now().date()

    task.save()

    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.ActionType.UPDATE,
        model_name='Task',
        object_id=str(task.id),
        description=f'Task status: {old_status} → {new_status}',
        ip_address=get_client_ip(request),
    )
    return JsonResponse({'status': new_status, 'label': task.get_status_display()})


@developer_required
def project_list(request):
    if request.user.is_admin:
        projects = Project.objects.annotate(task_count=Count('tasks')).order_by('-created_at')
    else:
        projects = Project.objects.filter(
            team_members=request.user
        ).annotate(task_count=Count('tasks')).order_by('-created_at')

    return render(request, 'developers/projects.html', {
        'projects': projects,
    })


@admin_required
def project_create(request):
    if request.method == 'POST':
        data = request.POST
        project = Project.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            start_date=data.get('start_date') or None,
            end_date=data.get('end_date') or None,
            created_by=request.user,
        )
        team_ids = request.POST.getlist('team_members')
        if team_ids:
            project.team_members.set(team_ids)

        messages.success(request, f'Project "{project.name}" created.')
        return redirect('developers:projects')

    developers = User.objects.filter(role=Role.DEVELOPER, is_active=True)
    return render(request, 'developers/project_form.html', {
        'developers': developers,
        'action': 'Create',
    })
