# Generated by Django 2.0.4 on 2018-05-25 23:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20180521_1822'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='halalivery_exclusive',
            field=models.NullBooleanField(default=False),
        ),
        migrations.AddField(
            model_name='vendor',
            name='hmc_approved',
            field=models.NullBooleanField(default=False),
        ),
    ]
