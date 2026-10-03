from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='excelimport',
            name='file_content',
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
    ]