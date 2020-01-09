# Generated by Django 2.1.2 on 2018-12-09 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0038_auto_20181018_1816'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='insurance_type',
            field=models.CharField(choices=[('zego', 'ZEGO Insurance'), ('other', '3rd party insurance provider'), ('not-required', 'Not required')], max_length=50, null=True),
        ),
    ]