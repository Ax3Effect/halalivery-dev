# Generated by Django 2.1.1 on 2018-09-18 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0035_auto_20180903_1754'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='insurance_type',
            field=models.CharField(choices=[(0, 'Car'), (1, 'Motorbike'), (2, 'Bicycle')], max_length=50, null=True),
        ),
    ]
