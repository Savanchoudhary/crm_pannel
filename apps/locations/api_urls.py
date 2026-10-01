from django.urls import path
from . import views

urlpatterns = [
    path('record/', views.record_location, name='api_record_location'),
    path('status/', views.tracking_status, name='api_tracking_status'),
    path('start/', views.start_tracking, name='api_start_tracking'),
    path('stop/', views.stop_tracking, name='api_stop_tracking'),
]
