"""
Accounts URL patterns.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profile (self)
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),

    # Employees (admin)
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/toggle/', views.employee_toggle_status, name='employee_toggle'),
    path('employees/<int:pk>/reset-password/', views.employee_reset_password, name='employee_reset_password'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    # Departments (admin)
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),

    # Activity Log (admin)
    path('activity/', views.activity_log, name='activity_log'),
]
