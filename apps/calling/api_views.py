from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import CallLog
from .serializers import CallLogSerializer
from apps.accounts.permissions import IsCallingUser


class CallLogListAPIView(ListAPIView):
    serializer_class = CallLogSerializer
    permission_classes = [IsCallingUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return CallLog.objects.select_related('lead', 'employee').all()
        return CallLog.objects.filter(employee=user).select_related('lead', 'employee')


class CallLogDetailAPIView(RetrieveUpdateAPIView):
    serializer_class = CallLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return CallLog.objects.all()
        return CallLog.objects.filter(employee=user)
