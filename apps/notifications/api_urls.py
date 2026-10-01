from django.urls import path
from . import views

urlpatterns = [
    path('mark-all-read/', views.mark_all_read, name='api_mark_all_read'),
    path('<int:pk>/read/', views.mark_read, name='api_mark_read'),
]
