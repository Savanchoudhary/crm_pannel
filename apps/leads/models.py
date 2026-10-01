"""
Leads models — Lead, LeadAssignment, Note, ExcelImport.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class LeadStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    CALLING = 'CALLING', _('Calling')
    COMPLETED = 'COMPLETED', _('Completed')
    NO_ANSWER = 'NO_ANSWER', _('No Answer')
    BUSY = 'BUSY', _('Busy')
    INTERESTED = 'INTERESTED', _('Interested')
    NOT_INTERESTED = 'NOT_INTERESTED', _('Not Interested')
    FOLLOW_UP = 'FOLLOW_UP', _('Follow-up Required')
    CONVERTED = 'CONVERTED', _('Converted')
    INVALID = 'INVALID', _('Invalid')


class LeadSource(models.TextChoices):
    EXCEL_UPLOAD = 'EXCEL', _('Excel Upload')
    MANUAL = 'MANUAL', _('Manual Entry')
    WEBSITE = 'WEBSITE', _('Website')
    REFERRAL = 'REFERRAL', _('Referral')
    COLD_CALL = 'COLD_CALL', _('Cold Call')
    SOCIAL_MEDIA = 'SOCIAL', _('Social Media')
    EMAIL_CAMPAIGN = 'EMAIL', _('Email Campaign')
    OTHER = 'OTHER', _('Other')


class Lead(models.Model):
    # Basic info
    name = models.CharField(max_length=200, db_index=True)
    company = models.CharField(max_length=200, blank=True, db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    alternate_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    location = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)

    # CRM tracking
    source = models.CharField(max_length=20, choices=LeadSource.choices, default=LeadSource.MANUAL)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.PENDING, db_index=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_leads', db_index=True
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_leads'
    )

    # Details
    remarks = models.TextField(blank=True)
    product_interest = models.CharField(max_length=200, blank=True)
    budget = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    # Flags
    is_duplicate = models.BooleanField(default=False)

    # Import tracking
    excel_import = models.ForeignKey(
        'ExcelImport', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leads'
    )

    # Timestamps
    last_called_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.name} — {self.phone}'

    @property
    def display_status_color(self):
        colors = {
            'PENDING': 'secondary',
            'CALLING': 'primary',
            'INTERESTED': 'success',
            'NOT_INTERESTED': 'danger',
            'FOLLOW_UP': 'info',
            'COMPLETED': 'success',
            'NO_ANSWER': 'warning',
            'BUSY': 'warning',
            'CONVERTED': 'success',
            'INVALID': 'dark',
        }
        return colors.get(self.status, 'secondary')


class LeadAssignment(models.Model):
    """Tracks assignment history of leads."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lead_assignments')
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='lead_assignments_made'
    )
    notes = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.lead} → {self.assigned_to}'


class Note(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='notes')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Note on {self.lead} by {self.created_by}'


class ExcelImport(models.Model):
    class ImportStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/excel/')
    status = models.CharField(
        max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING
    )
    total_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    duplicate_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    error_details = models.JSONField(default=dict)
    column_mapping = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Excel Import'
        verbose_name_plural = 'Excel Imports'

    def __str__(self):
        return f'{self.file_name} — {self.status} ({self.imported_rows} imported)'
