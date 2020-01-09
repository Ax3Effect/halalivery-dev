# Generated by Django 2.1.7 on 2019-04-01 10:26

import django.contrib.gis.db.models.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryPartnerDriver',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('firstname', models.CharField(blank=True, max_length=50, null=True)),
                ('lastname', models.CharField(blank=True, max_length=50, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('picture_path_imgix', models.CharField(blank=True, max_length=200, null=True)),
                ('transport_type', models.CharField(blank=True, max_length=20, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('point', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='DeliveryPartnerJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_id', models.IntegerField(blank=True, default=0, null=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('comment', models.CharField(blank=True, max_length=200, null=True)),
                ('pickup_at', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('dropoff_at', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('origin_comment', models.CharField(blank=True, max_length=200, null=True)),
                ('destination_comment', models.CharField(blank=True, max_length=200, null=True)),
                ('job_reference', models.CharField(blank=True, max_length=200, null=True)),
                ('current_delivery', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('transport_type', models.CharField(blank=True, max_length=200, null=True)),
                ('packageType', models.CharField(blank=True, max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DeliveryRoute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateField(auto_now=True)),
                ('latitude_from', models.FloatField(blank=True)),
                ('longitude_from', models.FloatField(blank=True)),
                ('latitude_to', models.FloatField(blank=True)),
                ('longitude_to', models.FloatField(blank=True)),
                ('origin_addresses', models.CharField(blank=True, max_length=300)),
                ('destination_addresses', models.CharField(blank=True, max_length=300)),
                ('distance', models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=6)),
                ('distance_text', models.CharField(blank=True, max_length=50)),
                ('duration', models.CharField(blank=True, max_length=50)),
                ('duration_text', models.CharField(blank=True, max_length=50)),
                ('driver_payout', models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=6)),
                ('route_type', models.CharField(blank=True, choices=[('driving', 'Driving'), ('walking', 'Walking'), ('bicycling', 'Bicycling')], max_length=50)),
                ('gateway_response', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('can_bicycle_deliver', models.BooleanField(blank=True, default=False)),
                ('can_motorcycle_deliver', models.BooleanField(blank=True, default=False)),
                ('can_car_deliver', models.BooleanField(blank=True, default=False)),
            ],
        ),
    ]