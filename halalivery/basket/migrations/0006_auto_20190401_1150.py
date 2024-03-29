# Generated by Django 2.1.7 on 2019-04-01 10:50

from django.db import migrations
import django_prices.models
import halalivery.core.utils.taxes


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0005_auto_20190325_2032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basket',
            name='driver_tip',
            field=django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12),
        ),
        migrations.AlterField(
            model_name='basket',
            name='subtotal',
            field=django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12),
        ),
        migrations.AlterField(
            model_name='basket',
            name='total',
            field=django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12),
        ),
    ]
