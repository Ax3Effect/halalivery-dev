# Generated by Django 2.0.4 on 2018-06-11 15:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20180610_0051'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vendor',
            name='address',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='city',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='longitude',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='phone',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='postcode',
        ),
    ]
