from django.contrib import admin
from .models import LocationRecord, TrackingSession


@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'started_at', 'ended_at', 'is_active', 'duration_display']
    list_filter = ['is_active']
    search_fields = ['employee__first_name', 'employee__last_name']


@admin.register(LocationRecord)
class LocationRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'latitude', 'longitude', 'accuracy', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['employee__first_name', 'employee__last_name']
    date_hierarchy = 'timestamp'
