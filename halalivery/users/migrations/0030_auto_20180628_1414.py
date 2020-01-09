# Generated by Django 2.0.4 on 2018-06-28 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_paymenttoken_customer_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='stripe_connect_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='companyhouse_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='stripe_connect_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
