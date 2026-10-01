from django.contrib import admin
from .models import Task, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'start_date', 'end_date', 'is_active']
    list_filter = ['status', 'is_active']
    filter_horizontal = ['team_members']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'developer', 'project', 'status', 'priority', 'due_date', 'is_overdue']
    list_filter = ['status', 'priority', 'due_date']
    search_fields = ['title', 'developer__first_name', 'developer__last_name']
    date_hierarchy = 'due_date'
