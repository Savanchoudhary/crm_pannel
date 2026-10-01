from django.contrib import admin
from .models import CallLog, FollowUp


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ['employee', 'lead', 'started_at', 'ended_at', 'duration_display', 'result', 'is_interested']
    list_filter = ['result', 'is_interested', 'started_at']
    search_fields = ['lead__name', 'lead__phone', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['duration_seconds', 'created_at', 'updated_at']
    date_hierarchy = 'started_at'


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['lead', 'assigned_to', 'follow_up_date', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'follow_up_date']
    search_fields = ['lead__name', 'assigned_to__first_name']
