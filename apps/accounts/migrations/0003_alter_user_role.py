from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_rename_calling_department'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMIN', _('Admin / Boss')),
                    ('CALLING', _('HR Department')),
                    ('MARKETING', _('Marketing')),
                    ('DEVELOPER', _('Developer')),
                ],
                default='CALLING',
                max_length=20,
            ),
        ),
    ]