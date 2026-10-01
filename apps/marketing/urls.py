from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    path('', views.marketing_home, name='home'),
    path('activities/', views.activity_list, name='activities'),
    path('activities/create/', views.activity_create, name='activity_create'),
]
