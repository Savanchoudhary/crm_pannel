from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('map/', views.admin_location_map, name='admin_map'),
    path('history/', views.admin_location_history, name='admin_history'),
    path('my/', views.my_location_history, name='my_history'),
    path('track/start/', views.start_tracking, name='start_tracking'),
    path('track/stop/', views.stop_tracking, name='stop_tracking'),
    path('track/status/', views.tracking_status, name='tracking_status'),
    path('track/record/', views.record_location, name='record_location'),
]
