# Generated by Django 2.0.4 on 2018-05-21 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20180521_1417'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenttoken',
            name='payment_method',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
