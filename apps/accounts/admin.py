"""
Django Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, EmployeeProfile, Department, ActivityLog


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'employee_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    extra = 0
    fields = [
        'department', 'employee_id', 'designation', 'status',
        'date_of_joining', 'can_view_calling', 'can_view_marketing', 'can_view_developers',
    ]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [EmployeeProfileInline]
    list_display = [
        'email', 'full_name', 'role', 'is_active',
        'last_seen_display', 'created_at'
    ]
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['first_name', 'last_name']
    readonly_fields = ['created_at', 'updated_at', 'last_seen']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Timestamps', {'fields': ('last_seen', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Name'

    def last_seen_display(self, obj):
        if obj.last_seen:
            return obj.last_seen.strftime('%Y-%m-%d %H:%M')
        return '—'
    last_seen_display.short_description = 'Last Seen'


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'department', 'designation', 'status']
    list_filter = ['department', 'status']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['employee_id', 'created_at', 'updated_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'description_short', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'description', 'model_name']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'description', 'ip_address', 'user_agent', 'created_at']

    def description_short(self, obj):
        return obj.description[:80] + '…' if len(obj.description) > 80 else obj.description
    description_short.short_description = 'Description'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
