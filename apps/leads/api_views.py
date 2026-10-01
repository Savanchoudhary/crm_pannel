from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Lead
from .serializers import LeadSerializer
from apps.accounts.permissions import IsAdminUser, IsCallingUser


class LeadListCreateAPIView(ListCreateAPIView):
    serializer_class = LeadSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'source', 'assigned_to']
    search_fields = ['name', 'phone', 'company', 'email']
    ordering_fields = ['created_at', 'updated_at', 'name']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Lead.objects.select_related('assigned_to').all()
        return Lead.objects.filter(assigned_to=user)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class LeadDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Lead.objects.all()
        return Lead.objects.filter(assigned_to=user)
