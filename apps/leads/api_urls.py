from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.LeadListCreateAPIView.as_view(), name='lead_list_api'),
    path('<int:pk>/', api_views.LeadDetailAPIView.as_view(), name='lead_detail_api'),
]
