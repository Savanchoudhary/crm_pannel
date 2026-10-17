from django.test import TestCase
from django.urls import reverse

from .templatetags.crm_tags import role_badge
from .models import User


class AdminDashboardActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email='dashboard-admin@example.com',
            password='test-password',
            username='dashboard-admin',
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_admin_dashboard_renders(self):
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HR Department')
        self.assertContains(response, 'Calls in Selected Range')
        self.assertContains(response, 'role=CALLING')
        self.assertContains(response, 'status=INTERESTED')
        self.assertContains(response, 'status=today')
        self.assertContains(response, 'status=overdue')

    def test_stat_cards_link_to_their_data_pages(self):
        response = self.client.get(reverse('dashboard:index'))
        expected_links = [
            reverse('accounts:employee_list'),
            f"{reverse('accounts:employee_list')}?role=CALLING",
            f"{reverse('accounts:employee_list')}?role=MARKETING",
            f"{reverse('accounts:employee_list')}?role=DEVELOPER",
            reverse('leads:list'),
            reverse('reports:calling'),
            f"{reverse('leads:list')}?status=INTERESTED",
            f"{reverse('calling:followups')}?status=today",
            f"{reverse('calling:followups')}?status=overdue",
        ]
        for link in expected_links:
            with self.subTest(link=link):
                self.assertContains(response, f'href="{link}')

    def test_quick_action_destinations_render_for_admin(self):
        destinations = [
            'leads:excel_upload',
            'leads:create',
            'accounts:employee_create',
            'developers:task_create',
            'calling:monitor',
            'reports:calling',
            'locations:admin_map',
            'notifications:announcement',
        ]

        for destination in destinations:
            with self.subTest(destination=destination):
                response = self.client.get(reverse(destination))
                self.assertEqual(response.status_code, 200)


class EmployeeRoleBadgeTests(TestCase):
    def test_employee_panel_renders_role_badge_as_html(self):
        admin = User.objects.create_superuser(
            email='role-badge-admin@example.com',
            password='test-password',
            username='role-badge-admin',
        )
        employee = User.objects.create_user(
            email='role-badge-employee@example.com',
            password='test-password',
            username='role-badge-employee',
            first_name='Test',
            role='ADMIN',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('accounts:employee_list'))

        self.assertContains(
            response, '<span class="badge bg-danger">Admin</span>', html=True
        )

    def test_role_badge_escapes_unexpected_role_labels(self):
        badge = role_badge('<script>alert(1)</script>')

        self.assertEqual(
            str(badge),
            '<span class="badge bg-secondary">'
            '&lt;script&gt;alert(1)&lt;/script&gt;</span>',
        )