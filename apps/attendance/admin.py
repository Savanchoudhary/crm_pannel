from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status', 'check_in_time', 'check_out_time', 'working_hours']
    list_filter = ['status', 'date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    date_hierarchy = 'date'
    readonly_fields = ['working_hours', 'created_at', 'updated_at']
