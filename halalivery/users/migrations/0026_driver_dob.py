# Generated by Django 2.0.4 on 2018-06-22 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_auto_20180621_2247'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='dob',
            field=models.DateField(null=True),
        ),
    ]
