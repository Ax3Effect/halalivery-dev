# Generated by Django 2.0.4 on 2018-05-21 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_paymenttoken_payment_method'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='payment',
        ),
        migrations.AddField(
            model_name='customer',
            name='payment_token',
            field=models.ManyToManyField(blank=True, related_name='payment_token', to='users.PaymentToken'),
        ),
    ]
