# Generated by Django 2.1.5 on 2019-03-25 20:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0004_auto_20190325_1953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basket',
            name='delivery_type',
            field=models.CharField(choices=[('delivery', 'Delivery'), ('pickup', 'Self pickup')], default='delivery', max_length=32),
        ),
    ]
