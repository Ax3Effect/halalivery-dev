# Generated by Django 2.1.7 on 2019-04-01 10:09

from decimal import Decimal
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0043_auto_20190324_2342'),
        ('menu', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Grocery',
            fields=[
                ('vendor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='grocery', serialize=False, to='users.Vendor')),
                ('online', models.BooleanField(default=True)),
                ('surcharge_amount', models.FloatField(blank=True, default=2.5, max_length=6)),
                ('surcharge_threshold', models.IntegerField(blank=True, default=10)),
                ('own_delivery', models.BooleanField(blank=True, default=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='MarketplaceVisibillity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='OperatingTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.IntegerField(choices=[(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')], default=1)),
                ('from_hour', models.TimeField()),
                ('to_hour', models.TimeField()),
            ],
            options={
                'ordering': ('weekday', 'from_hour'),
            },
        ),
        migrations.CreateModel(
            name='PrepTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('busy_status', models.CharField(choices=[('quiet', 'Quiet'), ('moderate', 'Moderate'), ('busy', 'Busy')], default='quiet', max_length=20)),
                ('quiet_time', models.PositiveSmallIntegerField(default=15)),
                ('moderate_time', models.PositiveSmallIntegerField(default=30)),
                ('busy_time', models.PositiveSmallIntegerField(default=45)),
            ],
        ),
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('vendor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='restaurant', serialize=False, to='users.Vendor')),
                ('online', models.BooleanField(default=True)),
                ('surcharge_amount', models.FloatField(blank=True, default=2.5, max_length=6)),
                ('surcharge_threshold', models.IntegerField(blank=True, default=10)),
                ('own_delivery', models.BooleanField(blank=True, default=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceableArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(default='Nottingham', max_length=50)),
                ('area', django.contrib.gis.db.models.fields.PolygonField(blank=True, default=None, null=True, srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='VendorCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('mood', models.CharField(choices=[('grocery', 'Grocery'), ('meat', 'Meat'), ('lunchy', 'Lunchy'), ('night_meal', 'Night meal'), ('night_meal', 'Movie night'), ('thirst', 'Thirst'), ('breakfast', 'Breakfast'), ('healthy', 'Healthy'), ('cheat', 'Cheat'), ('dessert', 'Dessert')], default='grocery', max_length=20)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='vendorcategory',
            unique_together={('name', 'mood')},
        ),
        migrations.AddField(
            model_name='restaurant',
            name='areas',
            field=models.ManyToManyField(to='marketplaces.ServiceableArea'),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='category',
            field=models.ManyToManyField(to='marketplaces.VendorCategory'),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='menu',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='restaurant_menu', to='menu.Menu'),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='operating_times',
            field=models.ManyToManyField(related_name='restaurants', to='marketplaces.OperatingTime'),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='prep_time',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='marketplaces.PrepTime'),
        ),
        migrations.AlterUniqueTogether(
            name='operatingtime',
            unique_together={('weekday', 'from_hour', 'to_hour')},
        ),
        migrations.AddField(
            model_name='grocery',
            name='areas',
            field=models.ManyToManyField(to='marketplaces.ServiceableArea'),
        ),
        migrations.AddField(
            model_name='grocery',
            name='category',
            field=models.ManyToManyField(to='marketplaces.VendorCategory'),
        ),
        migrations.AddField(
            model_name='grocery',
            name='menu',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='grocery_menu', to='menu.Menu'),
        ),
        migrations.AddField(
            model_name='grocery',
            name='operating_times',
            field=models.ManyToManyField(related_name='groceries', to='marketplaces.OperatingTime'),
        ),
        migrations.AddField(
            model_name='grocery',
            name='prep_time',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='marketplaces.PrepTime'),
        ),
    ]