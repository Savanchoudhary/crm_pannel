"""
Accounts serializers for REST API.
"""
from rest_framework import serializers
from .models import User, EmployeeProfile, Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'description', 'is_active']


class EmployeeProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            'employee_id', 'department', 'designation',
            'date_of_joining', 'status',
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = EmployeeProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone', 'is_active', 'last_seen', 'profile',
        ]
        read_only_fields = ['id', 'email', 'last_seen']
