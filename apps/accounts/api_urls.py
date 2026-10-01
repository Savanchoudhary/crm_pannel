"""
Accounts REST API URLs.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', api_views.CurrentUserView.as_view(), name='current_user'),
    path('employees/', api_views.EmployeeListAPIView.as_view(), name='employee_list_api'),
    path('employees/<int:pk>/', api_views.EmployeeDetailAPIView.as_view(), name='employee_detail_api'),
]
