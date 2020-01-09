# Generated by Django 2.1.7 on 2019-04-01 10:26

from decimal import Decimal
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_measurement.models
import django_prices.models
import halalivery.core.utils.json_serializer
import halalivery.core.utils.taxes
import halalivery.core.weight
import measurement.measures.mass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('coupons', '0009_auto_20181008_1720'),
        ('partner_discounts', '0007_auto_20190325_2032'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0043_auto_20190324_2342'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('time_placed', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('ready_for_pickup', 'Ready for pickup'), ('driver_arrived', 'Driver arrived'), ('driver_collected', 'Driver collected'), ('driver_delivered', 'Driver delivered'), ('canceled', 'Canceled'), ('self_picked_up', 'Self picked up')], default='draft', max_length=32)),
                ('language_code', models.CharField(default='en-us', max_length=35)),
                ('user_email', models.EmailField(blank=True, default='', max_length=254)),
                ('token', models.CharField(blank=True, max_length=36, unique=True)),
                ('prep_time', models.FloatField(max_length=6)),
                ('delivery_type', models.CharField(choices=[('delivery', 'Delivery'), ('pickup', 'Self pickup')], default='delivery', max_length=32)),
                ('delivery_by', models.CharField(choices=[('celery', 'Celery delivery'), ('stuart', 'Stuart delivery'), ('vendor', 'Vendor delivery')], default='celery', max_length=32)),
                ('confirmation_code', models.CharField(max_length=5)),
                ('delivery_fee', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('driver_tip', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('surcharge', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('subtotal', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('total_net', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('total_gross', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('discount_amount', django_prices.models.MoneyField(currency='GBP', decimal_places=2, default=halalivery.core.utils.taxes.zero_money, max_digits=12)),
                ('partner_discount_is_applied', models.BooleanField(default=False)),
                ('customer_note', models.TextField(blank=True, default='', null=True)),
                ('weight', django_measurement.models.MeasurementField(default=halalivery.core.weight.zero_weight, measurement=measurement.measures.mass.Mass)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_address', to='users.Address')),
                ('customer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='users.Customer')),
                ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='users.Driver')),
                ('partner_discount', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='partner_discounts.PartnerDiscount')),
                ('vendor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='users.Vendor')),
                ('voucher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='coupons.Coupon')),
            ],
            options={
                'ordering': ('-pk',),
                'permissions': (('manage_orders', 'Manage orders.'),),
            },
        ),
        migrations.CreateModel(
            name='OrderEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('type', models.CharField(choices=[('PLACED', 'placed'), ('VENDOR_ACCEPTED', 'vendor_accepted'), ('VENDOR_PREPARED', 'vendor_prepared'), ('DRIVER_ACCEPTED', 'driver_accepted'), ('DRIVER_CANCELED', 'driver_canceled'), ('DRIVER_PICKED_UP', 'driver_picked_up'), ('DRIVER_DELIVERED', 'driver_delivered'), ('PLACED_FROM_DRAFT', 'draft_placed'), ('OVERSOLD_ITEMS', 'oversold_items'), ('ORDER_MARKED_AS_PAID', 'marked_as_paid'), ('CANCELED', 'canceled'), ('ORDER_FULLY_PAID', 'order_paid'), ('UPDATED', 'updated'), ('EMAIL_SENT', 'email_sent'), ('PAYMENT_CAPTURED', 'captured'), ('PAYMENT_REFUNDED', 'refunded'), ('PAYMENT_VOIDED', 'voided'), ('FULFILLMENT_CANCELED', 'fulfillment_canceled'), ('FULFILLMENT_RESTOCKED_ITEMS', 'restocked_items'), ('FULFILLMENT_FULFILLED_ITEMS', 'fulfilled_items'), ('TRACKING_UPDATED', 'tracking_updated'), ('NOTE_ADDED', 'note_added'), ('OTHER', 'other')], max_length=255)),
                ('parameters', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, encoder=halalivery.core.utils.json_serializer.CustomJsonEncoder)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='order.Order')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('date',),
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=386, null=True)),
                ('translated_product_name', models.CharField(blank=True, default='', max_length=386)),
                ('product_sku', models.CharField(max_length=32, null=True)),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('quantity_fulfilled', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('unit_price_net', django_prices.models.MoneyField(currency='GBP', decimal_places=2, max_digits=12, null=True)),
                ('unit_price_gross', django_prices.models.MoneyField(currency='GBP', decimal_places=2, max_digits=12, null=True)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.0'), max_digits=5)),
                ('order', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='order.Order')),
            ],
            options={
                'ordering': ('pk',),
            },
        ),
        migrations.CreateModel(
            name='OrderItemMod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=386, null=True)),
                ('translated_product_name', models.CharField(blank=True, default='', max_length=386)),
                ('product_sku', models.CharField(max_length=32, null=True)),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('quantity_fulfilled', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('unit_price_net', django_prices.models.MoneyField(currency='GBP', decimal_places=2, max_digits=12, null=True)),
                ('unit_price_gross', django_prices.models.MoneyField(currency='GBP', decimal_places=2, max_digits=12, null=True)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.0'), max_digits=5)),
                ('order_line', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='mods', to='order.OrderItem')),
            ],
            options={
                'ordering': ('pk',),
            },
        ),
    ]
