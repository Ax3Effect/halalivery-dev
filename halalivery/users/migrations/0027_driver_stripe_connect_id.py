# Generated by Django 2.0.4 on 2018-06-22 17:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_driver_dob'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='stripe_connect_id',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
