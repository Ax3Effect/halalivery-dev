# Generated by Django 2.1.1 on 2018-09-14 13:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coupons', '0005_remove_couponuser_uses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='couponuser',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Customer', verbose_name='User'),
        ),
    ]
