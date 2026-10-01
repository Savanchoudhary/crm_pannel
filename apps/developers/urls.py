from django.urls import path
from . import views

app_name = 'developers'

urlpatterns = [
    path('', views.developer_home, name='home'),
    path('tasks/', views.task_list, name='tasks'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/status/', views.task_update_status, name='task_status'),
    path('projects/', views.project_list, name='projects'),
    path('projects/create/', views.project_create, name='project_create'),
]
