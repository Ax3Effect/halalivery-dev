# Generated by Django 2.0.4 on 2018-06-18 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_auto_20180611_1726'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='online',
            field=models.BooleanField(default=True),
        ),
    ]
