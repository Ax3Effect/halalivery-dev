# Generated by Django 2.1.7 on 2019-04-01 12:56

from decimal import Decimal
from django.db import migrations, models
import django_prices.models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='total_gross',
        ),
        migrations.RemoveField(
            model_name='order',
            name='total_net',
        ),
        migrations.AddField(
            model_name='order',
            name='total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='delivery_fee',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='driver_tip',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='surcharge',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='unit_price_gross',
            field=django_prices.models.MoneyField(currency=None, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='unit_price_net',
            field=django_prices.models.MoneyField(currency=None, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name='orderitemmod',
            name='unit_price_gross',
            field=django_prices.models.MoneyField(currency=None, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name='orderitemmod',
            name='unit_price_net',
            field=django_prices.models.MoneyField(currency=None, decimal_places=2, max_digits=12, null=True),
        ),
    ]