"""
Notifications model.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class NotificationType(models.TextChoices):
    LEAD_ASSIGNED = 'LEAD_ASSIGNED', _('Lead Assigned')
    FOLLOW_UP = 'FOLLOW_UP', _('Follow-up Reminder')
    FOLLOW_UP_OVERDUE = 'FOLLOW_UP_OVERDUE', _('Follow-up Overdue')
    TASK_ASSIGNED = 'TASK_ASSIGNED', _('Task Assigned')
    TASK_DUE = 'TASK_DUE', _('Task Due Soon')
    TASK_COMPLETED = 'TASK_COMPLETED', _('Task Completed')
    ANNOUNCEMENT = 'ANNOUNCEMENT', _('Announcement')
    SYSTEM = 'SYSTEM', _('System')


class Notification(models.Model):
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices, default=NotificationType.SYSTEM
    )
    is_read = models.BooleanField(default=False, db_index=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    action_url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]

    def __str__(self):
        return f'{self.recipient.full_name} — {self.title}'

    @property
    def icon(self):
        icons = {
            'LEAD_ASSIGNED': 'bi-person-plus',
            'FOLLOW_UP': 'bi-calendar-check',
            'FOLLOW_UP_OVERDUE': 'bi-exclamation-triangle',
            'TASK_ASSIGNED': 'bi-clipboard-plus',
            'TASK_DUE': 'bi-clock',
            'TASK_COMPLETED': 'bi-check-circle',
            'ANNOUNCEMENT': 'bi-megaphone',
            'SYSTEM': 'bi-bell',
        }
        return icons.get(self.notification_type, 'bi-bell')
