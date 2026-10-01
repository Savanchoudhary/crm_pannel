"""
Marketing models — MarketingActivity, Campaign, Task.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class ActivityType(models.TextChoices):
    FIELD_VISIT = 'FIELD_VISIT', _('Field Visit')
    DEMO = 'DEMO', _('Product Demo')
    EXHIBITION = 'EXHIBITION', _('Exhibition / Trade Show')
    MEETING = 'MEETING', _('Client Meeting')
    CANVASSING = 'CANVASSING', _('Canvassing')
    DISTRIBUTION = 'DISTRIBUTION', _('Material Distribution')
    OTHER = 'OTHER', _('Other')


class ActivityStatus(models.TextChoices):
    PLANNED = 'PLANNED', _('Planned')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class MarketingActivity(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='marketing_activities')
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=ActivityStatus.choices, default=ActivityStatus.PLANNED)
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    contacts_met = models.IntegerField(default=0)
    leads_generated = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Marketing Activity'
        verbose_name_plural = 'Marketing Activities'
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['status', 'date']),
        ]

    def __str__(self):
        return f'{self.employee.full_name} — {self.title} ({self.date})'


class Campaign(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    team_members = models.ManyToManyField(User, related_name='campaigns', blank=True)
    target = models.IntegerField(default=0, help_text='Target leads/conversions')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name
