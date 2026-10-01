"""
Calling models — CallLog, FollowUp.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.leads.models import Lead


class CallResult(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    CALLING = 'CALLING', _('Calling (In Progress)')
    COMPLETED = 'COMPLETED', _('Completed')
    NO_ANSWER = 'NO_ANSWER', _('No Answer')
    BUSY = 'BUSY', _('Busy')
    INTERESTED = 'INTERESTED', _('Interested')
    NOT_INTERESTED = 'NOT_INTERESTED', _('Not Interested')
    FOLLOW_UP = 'FOLLOW_UP', _('Follow-up Required')
    WRONG_NUMBER = 'WRONG_NUMBER', _('Wrong Number')
    SWITCHED_OFF = 'SWITCHED_OFF', _('Phone Switched Off')
    CALLBACK = 'CALLBACK', _('Requested Callback')


class CallLog(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='call_logs')
    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='call_logs')

    # Time tracking
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)  # Calculated on end

    # Result
    result = models.CharField(max_length=20, choices=CallResult.choices, default=CallResult.PENDING)
    notes = models.TextField(blank=True)
    is_interested = models.BooleanField(null=True, blank=True)

    # Follow-up flag
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Call Log'
        verbose_name_plural = 'Call Logs'
        indexes = [
            models.Index(fields=['employee', 'started_at']),
            models.Index(fields=['lead', 'started_at']),
            models.Index(fields=['result', 'started_at']),
        ]

    def __str__(self):
        return f'{self.employee} → {self.lead} @ {self.started_at:%Y-%m-%d %H:%M}'

    def save(self, *args, **kwargs):
        # Auto-calculate duration
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            self.duration_seconds = max(0, int(delta.total_seconds()))
        super().save(*args, **kwargs)

    @property
    def duration_display(self):
        s = self.duration_seconds
        if not s:
            return '—'
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f'{h}h {m}m {sec}s'
        elif m:
            return f'{m}m {sec}s'
        return f'{sec}s'

    @property
    def is_active(self):
        return self.result == CallResult.CALLING


class FollowUp(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    call_log = models.ForeignKey(
        CallLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='followups'
    )
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='followups')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_followups')

    follow_up_date = models.DateField(db_index=True)
    follow_up_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['follow_up_date', 'follow_up_time']
        verbose_name = 'Follow-up'
        verbose_name_plural = 'Follow-ups'
        indexes = [
            models.Index(fields=['assigned_to', 'follow_up_date', 'is_completed']),
        ]

    def __str__(self):
        return f'Follow-up: {self.lead} on {self.follow_up_date}'

    @property
    def is_overdue(self):
        from django.utils import timezone
        return not self.is_completed and self.follow_up_date < timezone.now().date()
