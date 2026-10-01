from django.urls import path
from . import views

app_name = 'calling'

urlpatterns = [
    path('', views.calling_home, name='home'),
    path('monitor/', views.call_monitor, name='monitor'),
    path('followups/', views.followup_list, name='followups'),
    path('followups/<int:pk>/complete/', views.complete_followup, name='complete_followup'),
    path('start/<int:lead_pk>/', views.start_call, name='start_call'),
    path('end/<int:call_pk>/', views.end_call, name='end_call'),
]
