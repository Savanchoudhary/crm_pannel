from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import json
import re

from apps.accounts.models import Role, User
from .models import Student, StudentAttendance, StudentAttendanceStatus, StudentTechnology


class StudentAttendanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.developer = User.objects.create_user(
            email='developer-attendance@example.com',
            username='developer-attendance',
            password='test-password',
            role=Role.DEVELOPER,
        )
        cls.admin = User.objects.create_user(
            email='admin-attendance@example.com',
            username='admin-attendance',
            password='test-password',
            role=Role.ADMIN,
        )
        cls.calling_user = User.objects.create_user(
            email='calling-attendance@example.com',
            username='calling-attendance',
            password='test-password',
            role=Role.CALLING,
        )

    def test_developer_can_add_student_and_mark_attendance(self):
        self.client.force_login(self.developer)
        page_url = reverse('attendance:student_attendance')
        add_response = self.client.post(page_url, {
            'action': 'add_student',
            'name': 'Asha Student',
            'phone': '9876543210',
            'new_student_technology': StudentTechnology.PYTHON_AI_ML,
            'date': '2026-10-01',
        })
        self.assertEqual(add_response.status_code, 302)
        student = Student.objects.get(name='Asha Student')

        page_response = self.client.get(page_url, {
            'date': '2026-10-01',
            'technology': StudentTechnology.PYTHON_AI_ML,
        })
        self.assertContains(page_response, 'Python with AI/ML')
        self.assertContains(page_response, 'Asha Student')
        self.assertContains(page_response, 'Student Attendance')

        response = self.client.post(page_url, {
            'action': 'mark_attendance',
            'date': '2026-10-01',
            'technology': StudentTechnology.PYTHON_AI_ML,
            f'status_{student.pk}': StudentAttendanceStatus.PRESENT,
        })

        self.assertEqual(response.status_code, 302)
        attendance = StudentAttendance.objects.get(student=student, date='2026-10-01')
        self.assertEqual(attendance.status, StudentAttendanceStatus.PRESENT)
        self.assertEqual(attendance.marked_by, self.developer)

    def test_only_developer_role_can_access_student_attendance(self):
        page_url = reverse('attendance:student_attendance')
        for user in (self.admin, self.calling_user):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 403)


class EmployeeLocationScopeTests(TestCase):
    def test_admin_map_shows_calling_and_marketing_only(self):
        admin = User.objects.create_superuser(
            email='location-admin@example.com',
            username='location-admin',
            password='test-password',
        )
        users = [
            User.objects.create_user(
                email=f'{role.lower()}-location@example.com',
                username=f'{role.lower()}-location',
                password='test-password',
                role=role,
                first_name=role,
            )
            for role in (Role.CALLING, Role.MARKETING, Role.DEVELOPER)
        ]
        from apps.locations.models import LocationRecord

        for user in users:
            LocationRecord.objects.create(
                employee=user,
                latitude=10.0,
                longitude=20.0,
                timestamp=timezone.now(),
            )

        self.client.force_login(admin)
        response = self.client.get(reverse('locations:admin_map'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tile.openstreetmap.de')
        visible_ids = {item['id'] for item in response.context['employee_locations']}
        self.assertEqual(visible_ids, {users[0].id, users[1].id})
        payload = re.search(
            r'<script id="employee-locations-data" type="application/json">(.*?)</script>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(payload)
        self.assertEqual({item['id'] for item in json.loads(payload.group(1))}, visible_ids)