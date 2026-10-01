from django.contrib import admin
from .models import Lead, LeadAssignment, Note, ExcelImport


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'phone', 'email', 'status', 'source', 'assigned_to', 'created_at']
    list_filter = ['status', 'source', 'created_at']
    search_fields = ['name', 'phone', 'email', 'company']
    readonly_fields = ['created_at', 'updated_at', 'last_called_at']
    list_per_page = 50
    date_hierarchy = 'created_at'


@admin.register(ExcelImport)
class ExcelImportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'uploaded_by', 'status', 'total_rows', 'imported_rows', 'duplicate_rows', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['lead', 'created_by', 'content_short', 'created_at']
    readonly_fields = ['created_at']

    def content_short(self, obj):
        return obj.content[:60]
    content_short.short_description = 'Content'
