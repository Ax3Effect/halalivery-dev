# Generated by Django 2.0.4 on 2018-06-06 12:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20180605_1947'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='driver',
            name='address',
        ),
        migrations.AddField(
            model_name='driver',
            name='address',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Address'),
        ),
    ]
