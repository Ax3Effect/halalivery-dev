# Generated by Django 2.0.4 on 2018-06-25 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_vendor_companyhouse_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenttoken',
            name='customer_id',
            field=models.CharField(blank=True, max_length=60),
        ),
    ]
