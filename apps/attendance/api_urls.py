from django.urls import path
from . import views

urlpatterns = [
    path('check-in/', views.check_in, name='api_check_in'),
    path('check-out/', views.check_out, name='api_check_out'),
    path('status/', views.attendance_status, name='api_attendance_status'),
]
