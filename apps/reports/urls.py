from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_home, name='home'),
    path('calling/', views.calling_report, name='calling'),
    path('attendance/', views.attendance_report_view, name='attendance'),
    path('developers/', views.developer_report, name='developers'),
]
