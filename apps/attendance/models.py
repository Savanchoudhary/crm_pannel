"""
Attendance model — daily check-in/check-out.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import EmployeeProfile


class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', _('Present')
    ABSENT = 'ABSENT', _('Absent')
    HALF_DAY = 'HALF_DAY', _('Half Day')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')
    HOLIDAY = 'HOLIDAY', _('Holiday')


class Attendance(models.Model):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name='attendance_records'
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    check_in_location = models.CharField(max_length=200, blank=True)
    check_out_location = models.CharField(max_length=200, blank=True)
    check_in_lat = models.FloatField(null=True, blank=True)
    check_in_lng = models.FloatField(null=True, blank=True)
    check_out_lat = models.FloatField(null=True, blank=True)
    check_out_lng = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = [('employee', 'date')]
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        indexes = [
            models.Index(fields=['employee', 'date']),
        ]

    def __str__(self):
        return f'{self.employee.user.full_name} — {self.date} — {self.status}'

    def save(self, *args, **kwargs):
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            self.working_hours = round(delta.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    @property
    def is_checked_in(self):
        return self.check_in_time is not None and self.check_out_time is None

    @property
    def working_hours_display(self):
        if not self.working_hours:
            return '—'
        h = int(self.working_hours)
        m = int((self.working_hours - h) * 60)
        return f'{h}h {m}m'


class StudentTechnology(models.TextChoices):
    PYTHON_AI_ML = 'PYTHON_AI_ML', _('Python with AI/ML')
    PYTHON_DATA_ANALYSIS = 'PYTHON_DATA_ANALYSIS', _('Python with Data Analysis')
    FULL_STACK = 'FULL_STACK', _('Full Stack Development')
    ANDROID = 'ANDROID', _('Android Development')
    DIGITAL_MARKETING = 'DIGITAL_MARKETING', _('Digital Marketing')
    GRAPHICS_DESIGNING = 'GRAPHICS_DESIGNING', _('Graphics Designing')
    CYBER_SECURITY = 'CYBER_SECURITY', _('Cyber Security')
    IOT = 'IOT', _('IoT')
    EMBEDDED_SYSTEM = 'EMBEDDED_SYSTEM', _('Embedded System')
    PHP = 'PHP', _('PHP')
    AUTOCAD = 'AUTOCAD', _('AutoCAD')


class StudentAttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', _('Present')
    ABSENT = 'ABSENT', _('Absent')
    HALF_DAY = 'HALF_DAY', _('Half Day')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')


class Student(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    technology = models.CharField(max_length=30, choices=StudentTechnology.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['technology', 'name']

    def __str__(self):
        return f'{self.name} — {self.get_technology_display()}'


class StudentAttendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=StudentAttendanceStatus.choices)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_student_attendance',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student__technology', 'student__name']
        constraints = [
            models.UniqueConstraint(fields=['student', 'date'], name='unique_student_attendance_per_day'),
        ]

    def __str__(self):
        return f'{self.student.name} — {self.date} — {self.get_status_display()}'
