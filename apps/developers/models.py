"""
Developers models — Project, Task.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    ON_HOLD = 'ON_HOLD', _('On Hold')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class TaskPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class Project(models.Model):
    class ProjectStatus(models.TextChoices):
        PLANNING = 'PLANNING', _('Planning')
        ACTIVE = 'ACTIVE', _('Active')
        ON_HOLD = 'ON_HOLD', _('On Hold')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNING
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    team_members = models.ManyToManyField(User, related_name='projects', blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_projects'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def completion_percentage(self):
        total = self.tasks.exclude(status=TaskStatus.CANCELLED).count()
        if not total:
            return 0
        done = self.tasks.filter(status=TaskStatus.COMPLETED).count()
        return round((done / total) * 100)


class Task(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True
    )
    developer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks')

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING, db_index=True)
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_date = models.DateField(null=True, blank=True)

    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        indexes = [
            models.Index(fields=['developer', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.due_date and
            self.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS] and
            self.due_date < timezone.now().date()
        )

    @property
    def priority_color(self):
        return {
            'LOW': 'success',
            'MEDIUM': 'warning',
            'HIGH': 'danger',
            'CRITICAL': 'dark',
        }.get(self.priority, 'secondary')
