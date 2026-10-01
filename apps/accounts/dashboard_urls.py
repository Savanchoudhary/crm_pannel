"""
Dashboard URL patterns (role-based routing).
"""
from django.urls import path
from .dashboard_views import dashboard_index

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_index, name='index'),
]
