"""
Location tracking models — explicit consent-based only.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class TrackingSession(models.Model):
    """Represents a consent-based tracking session started by the employee."""
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracking_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.employee.full_name} — session {self.id}'

    @property
    def duration_display(self):
        if not self.ended_at:
            return 'Active'
        delta = self.ended_at - self.started_at
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f'{h}h {m}m'


class LocationRecord(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_records')
    session = models.ForeignKey(
        TrackingSession, on_delete=models.CASCADE,
        related_name='records', null=True, blank=True
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy = models.FloatField(null=True, blank=True, help_text='Accuracy in meters')
    altitude = models.FloatField(null=True, blank=True)
    address = models.CharField(max_length=300, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    is_check_in = models.BooleanField(default=False)
    is_check_out = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Location Record'
        verbose_name_plural = 'Location Records'
        indexes = [
            models.Index(fields=['employee', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.employee.full_name} @ ({self.latitude:.4f}, {self.longitude:.4f}) {self.timestamp:%Y-%m-%d %H:%M}'
