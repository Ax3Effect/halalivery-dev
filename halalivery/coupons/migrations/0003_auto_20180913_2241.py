# Generated by Django 2.1.1 on 2018-09-13 21:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupons', '0002_coupon_min_amount_spent'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='usage_limit',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='coupon',
            name='used',
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
    ]