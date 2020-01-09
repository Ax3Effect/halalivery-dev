# Generated by Django 2.1.5 on 2019-03-25 18:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coupons', '0009_auto_20181008_1720'),
        ('partner_discounts', '0005_partnerdiscount_name'),
        ('basket', '0002_basket_voucher_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='basket',
            name='discount_amount',
        ),
        migrations.RemoveField(
            model_name='basket',
            name='discount_name',
        ),
        migrations.RemoveField(
            model_name='basket',
            name='partner_discount_amount',
        ),
        migrations.RemoveField(
            model_name='basket',
            name='partner_discount_name',
        ),
        migrations.RemoveField(
            model_name='basket',
            name='voucher_code',
        ),
        migrations.AddField(
            model_name='basket',
            name='partner_discount',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='partner_discounts.PartnerDiscount'),
        ),
        migrations.AddField(
            model_name='basket',
            name='voucher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='coupons.Coupon'),
        ),
    ]