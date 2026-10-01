from rest_framework import serializers
from .models import Lead, Note


class NoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Note
        fields = ['id', 'content', 'created_by_name', 'created_at']


class LeadSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'company', 'phone', 'email', 'location',
            'source', 'status', 'status_display', 'assigned_to', 'assigned_to_name',
            'remarks', 'product_interest', 'last_called_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
