from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.my_attendance, name='my_attendance'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('status/', views.attendance_status, name='status'),
    path('report/', views.attendance_report, name='report'),
    path('students/', views.student_attendance, name='student_attendance'),
]
