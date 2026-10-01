"""
Management command: setup_crm
Creates initial departments, admin user, and sample employees.
Usage: python manage.py setup_crm
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, Department, EmployeeProfile, Role


class Command(BaseCommand):
    help = 'Set up initial CRM data: departments and admin user.'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admin@novemcontrols.com')
        parser.add_argument('--password', type=str, default='Admin@1234')
        parser.add_argument('--with-sample-data', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Novem Controls CRM Setup ===\n'))

        # ── Create Departments ─────────────────────────────────────────────
        departments = [
            {'name': 'HR Department', 'code': 'CALL', 'description': 'Human resources and employee support'},
            {'name': 'Marketing', 'code': 'MKT', 'description': 'Field marketing and promotions'},
            {'name': 'Development', 'code': 'DEV', 'description': 'Software development team'},
            {'name': 'Administration', 'code': 'ADMIN', 'description': 'Management and administration'},
        ]
        for dept_data in departments:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            if not created and dept.name == 'Calling':
                dept.name = dept_data['name']
                dept.description = dept_data['description']
                dept.save(update_fields=['name', 'description', 'updated_at'])
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'  Department: {dept.name} — {status}')

        # ── Create Admin User ──────────────────────────────────────────────
        email = options['email']
        password = options['password']
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'\n  Admin user already exists: {email}'))
        else:
            admin = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Admin',
                last_name='Boss',
                username='admin',
            )
            admin_dept = Department.objects.get(code='ADMIN')
            EmployeeProfile.objects.filter(user=admin).update(department=admin_dept)
            self.stdout.write(self.style.SUCCESS(f'\n  Admin user created: {email}'))
            self.stdout.write(self.style.WARNING(f'  Password: {password} ← CHANGE THIS IN PRODUCTION!'))

        # ── Sample Data ────────────────────────────────────────────────────
        if options['with_sample_data']:
            self._create_sample_employees()

        self.stdout.write(self.style.SUCCESS('\n=== Setup Complete ===\n'))
        self.stdout.write('  Run: python manage.py runserver')
        self.stdout.write('  Visit: http://127.0.0.1:8000/')

    def _create_sample_employees(self):
        self.stdout.write('\n  Creating sample employees...')
        calling_dept = Department.objects.get(code='CALL')
        marketing_dept = Department.objects.get(code='MKT')
        dev_dept = Department.objects.get(code='DEV')

        sample_users = [
            {'email': 'calling1@novemcontrols.com', 'first_name': 'Rahul', 'last_name': 'Sharma',
             'role': Role.CALLING, 'dept': calling_dept},
            {'email': 'calling2@novemcontrols.com', 'first_name': 'Priya', 'last_name': 'Patel',
             'role': Role.CALLING, 'dept': calling_dept},
            {'email': 'marketing1@novemcontrols.com', 'first_name': 'Amit', 'last_name': 'Singh',
             'role': Role.MARKETING, 'dept': marketing_dept},
            {'email': 'dev1@novemcontrols.com', 'first_name': 'Neha', 'last_name': 'Kumar',
             'role': Role.DEVELOPER, 'dept': dev_dept},
        ]

        for data in sample_users:
            dept = data.pop('dept')
            email = data['email']
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    password='Employee@1234',
                    username=email.split('@')[0],
                    **data
                )
                EmployeeProfile.objects.filter(user=user).update(department=dept)
                self.stdout.write(f'    Created: {user.full_name} ({user.role})')
            else:
                self.stdout.write(f'    Exists: {email}')
