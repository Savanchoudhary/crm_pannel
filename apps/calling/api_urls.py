from django.urls import path
from . import api_views

urlpatterns = [
    path('logs/', api_views.CallLogListAPIView.as_view(), name='call_log_list'),
    path('logs/<int:pk>/', api_views.CallLogDetailAPIView.as_view(), name='call_log_detail'),
]
