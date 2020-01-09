# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.shortcuts import get_object_or_404
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from operator import attrgetter
from prices import Money
from django_prices.models import MoneyField, TaxedMoneyField

from . import WeekDay, Moods, BusyStatus
from halalivery.users.models import Vendor, Customer, Driver, Address
from halalivery.menu.models import Menu
from .utils import is_open


# Create your models here.

class ServiceableArea(models.Model):
    city = models.CharField(max_length=50, default='Nottingham')
    area = models.PolygonField(default=None, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.city)

class VendorCategory(models.Model):
    name = models.CharField(max_length=50)
    mood = models.CharField(max_length=20, choices=Moods.CHOICES, default=Moods.GROCERY)

    class Meta:
        unique_together = ('name', 'mood')

    def __str__(self):
        return "{} - {}".format(self.name, self.get_mood_display())

class PrepTime(models.Model):
    busy_status = models.CharField(max_length=20, choices=BusyStatus.CHOICES, default=BusyStatus.QUIET)
    quiet_time = models.PositiveSmallIntegerField(default=15)
    moderate_time = models.PositiveSmallIntegerField(default=30)
    busy_time = models.PositiveSmallIntegerField(default=45)

    def __str__(self):
        return f"{self.get_busy_status_display()}: {self.quiet_time} / {self.moderate_time} / {self.busy_time}"

    def time(self):
        time = {
            BusyStatus.QUIET: self.quiet_time,
            BusyStatus.MODERATE: self.moderate_time,
            BusyStatus.BUSY: self.busy_time
        }
        return time[self.busy_status]

class OperatingTime(models.Model):
    weekday = models.IntegerField(choices=WeekDay.CHOICES, default=WeekDay.MONDAY)
    from_hour = models.TimeField()
    to_hour = models.TimeField()

    class Meta:
        ordering = ('weekday', 'from_hour')
        unique_together = ('weekday', 'from_hour', 'to_hour')

    def __str__(self):
        return f"{self.get_weekday_display()}: {self.from_hour} - {self.to_hour}"

class AvailableVendorManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset().filter(online=True)
        vendors = [_qs.vendor for _qs in qs if _qs.is_available()]
        return super().get_queryset().filter(vendor__in=vendors)

class Grocery(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, primary_key=True, related_name="grocery")
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True, related_name="grocery_menu")
    areas = models.ManyToManyField(ServiceableArea)
    category = models.ManyToManyField(VendorCategory)
    operating_times = models.ManyToManyField(OperatingTime, related_name='groceries')
    online = models.BooleanField(default=True)
    prep_time = models.OneToOneField(PrepTime, on_delete=models.CASCADE)
    surcharge_threshold = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=15)
    own_delivery = models.BooleanField(default=False, blank=True, null=True)

    objects = models.Manager()
    available_groceries = AvailableVendorManager()

    def __str__(self):
        return self.vendor.vendor_name

    def is_available(self):
        _online = self.online
        if not _online:
            return False

        now = timezone.localtime(timezone.now()).replace(microsecond=0)
        return is_open(marketplace=self, now=now)

class Restaurant(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE,
                                  primary_key=True, related_name="restaurant")
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True, related_name="restaurant_menu")
    areas = models.ManyToManyField(ServiceableArea)
    category = models.ManyToManyField(VendorCategory)
    operating_times = models.ManyToManyField(OperatingTime, related_name='restaurants')
    online = models.BooleanField(default=True)
    prep_time = models.OneToOneField(PrepTime, on_delete=models.CASCADE)
    surcharge_threshold = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=15)
    own_delivery = models.BooleanField(default=False, blank=True, null=True)

    objects = models.Manager()
    available_restaurants = AvailableVendorManager()

    def __str__(self):
        return self.vendor.vendor_name

    def is_available(self):
        _online = self.online
        if not _online:
            return False
        now = timezone.localtime(timezone.now()).replace(microsecond=0)
        return is_open(marketplace=self, now=now)

class MarketplaceVisibillity(models.Model):
    distance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return '{}'.format(self.distance)
