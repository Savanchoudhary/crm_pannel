"""
Novem Controls CRM — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

    # Accounts (auth)
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),

    # Dashboard (role-based redirect)
    path('dashboard/', include('apps.accounts.dashboard_urls', namespace='dashboard')),

    # Leads
    path('leads/', include('apps.leads.urls', namespace='leads')),

    # Calling
    path('calling/', include('apps.calling.urls', namespace='calling')),

    # Marketing
    path('marketing/', include('apps.marketing.urls', namespace='marketing')),

    # Developers
    path('developers/', include('apps.developers.urls', namespace='developers')),

    # Attendance
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),

    # Locations
    path('locations/', include('apps.locations.urls', namespace='locations')),

    # Reports
    path('reports/', include('apps.reports.urls', namespace='reports')),

    # Notifications
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),

    # REST API v1
    path('api/v1/', include([
        path('accounts/', include('apps.accounts.api_urls')),
        path('leads/', include('apps.leads.api_urls')),
        path('calling/', include('apps.calling.api_urls')),
        path('attendance/', include('apps.attendance.api_urls')),
        path('locations/', include('apps.locations.api_urls')),
        path('notifications/', include('apps.notifications.api_urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site branding
admin.site.site_header = 'Novem Controls CRM'
admin.site.site_title = 'Novem Controls Admin'
admin.site.index_title = 'CRM Administration'
