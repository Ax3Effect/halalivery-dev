# Generated by Django 2.1.1 on 2018-09-14 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupons', '0003_auto_20180913_2241'),
    ]

    operations = [
        migrations.AddField(
            model_name='couponuser',
            name='uses',
            field=models.SmallIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='usage_limit',
            field=models.PositiveIntegerField(blank=True, help_text='How many times a coupon can be used.', null=True),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='used',
            field=models.PositiveIntegerField(default=0, verbose_name='Used'),
        ),
    ]