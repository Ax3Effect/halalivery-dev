# Generated by Django 2.0.4 on 2018-06-21 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_remove_vendor_online'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='dob',
            field=models.DateField(null=True),
        ),
    ]