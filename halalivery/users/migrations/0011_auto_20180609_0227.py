# Generated by Django 2.0.4 on 2018-06-09 02:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_driver_online'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(
            model_name='driver',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='driver',
            name='longitude',
        ),
        migrations.AddField(
            model_name='driver',
            name='location',
            field=models.ManyToManyField(blank=True, null=True, to='users.Location'),
        ),
    ]
