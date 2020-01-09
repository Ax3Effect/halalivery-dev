# Generated by Django 2.1.7 on 2019-04-01 12:41

from django.db import migrations
import django_prices.models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplaces', '0002_auto_20190401_1235'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grocery',
            name='surcharge_threshold',
            field=django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=15, max_digits=12),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='surcharge_threshold',
            field=django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=15, max_digits=12),
        ),
    ]