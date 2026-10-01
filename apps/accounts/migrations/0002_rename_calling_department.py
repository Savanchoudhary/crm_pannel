from django.db import migrations


def rename_calling_department(apps, schema_editor):
    Department = apps.get_model('accounts', 'Department')
    Department.objects.filter(code='CALL').update(
        name='HR Department',
        description='Human resources and employee support',
    )


def restore_calling_department(apps, schema_editor):
    Department = apps.get_model('accounts', 'Department')
    Department.objects.filter(code='CALL').update(
        name='Calling',
        description='Outbound calling and lead follow-up',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(rename_calling_department, restore_calling_department),
    ]