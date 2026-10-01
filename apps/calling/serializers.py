from rest_framework import serializers
from .models import CallLog, FollowUp


class CallLogSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    duration_display = serializers.CharField(read_only=True)

    class Meta:
        model = CallLog
        fields = [
            'id', 'lead', 'lead_name', 'employee', 'employee_name',
            'started_at', 'ended_at', 'duration_seconds', 'duration_display',
            'result', 'notes', 'is_interested', 'follow_up_required', 'follow_up_date',
            'created_at',
        ]
        read_only_fields = ['id', 'duration_seconds', 'created_at']


class FollowUpSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            'id', 'lead', 'lead_name', 'assigned_to', 'assigned_to_name',
            'follow_up_date', 'follow_up_time', 'notes',
            'is_completed', 'completed_at', 'is_overdue', 'created_at',
        ]
