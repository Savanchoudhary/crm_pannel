from django.contrib import admin
from .models import MarketingActivity, Campaign


@admin.register(MarketingActivity)
class MarketingActivityAdmin(admin.ModelAdmin):
    list_display = ['employee', 'title', 'activity_type', 'status', 'date', 'leads_generated']
    list_filter = ['activity_type', 'status', 'date']
    search_fields = ['employee__first_name', 'title']
    date_hierarchy = 'date'


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'target']
    list_filter = ['is_active']
    filter_horizontal = ['team_members']
