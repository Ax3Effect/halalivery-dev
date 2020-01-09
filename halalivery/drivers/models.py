from django.contrib.gis.db import models
from django.utils import timezone
from datetime import datetime, timedelta, time
from operator import attrgetter

from django.contrib.postgres.fields import JSONField
from halalivery.users.models import Driver
from halalivery.order.models import Order
from halalivery.delivery import RouteType
# Create your models here.

class DriverAvailability(models.Model):
    available_from = models.TimeField(blank=True)
    available_to = models.TimeField(blank=True)
    
    def __str__(self):
        return "#{} Available from {} to {}".format(self.id, self.available_from, self.available_to)
    
    def is_available(self):
        now = timezone.localtime(timezone.now())
        now_time = now.time()
        #availability = self
        # available_from = time(10, 00, 00)
        # available_until = time(23, 00, 00)
        available_from = self.available_from#time(10, 00, 00)
        available_until = self.available_to#time(23, 00, 00)
        return available_from < now_time < available_until

class DriverPayout(models.Model):
    minimum = models.DecimalField(blank=True, default=4.0, decimal_places=2, max_digits=6)
    maximum = models.DecimalField(blank=True, default=6.0, decimal_places=2, max_digits=6)
    per_mile = models.DecimalField(blank=True, default=1.35, decimal_places=2, max_digits=6)
    multiplier = models.DecimalField(blank=True, default=1.5, decimal_places=2, max_digits=6)
    base_miles = models.DecimalField(blank=True, default=1.5, decimal_places=2, max_digits=6)

    def __str__(self):
        return "#{} Minimum {} Maximum {} Per mile {} Multiplier {}".format(self.id, self.minimum, self.maximum, self.per_mile, self.multiplier)

class DriverOrderVisibility(models.Model):
    bicycle_radius = models.DecimalField(help_text="Set radius in miles", default=1.5, decimal_places=2, max_digits=6, blank=False)
    bicycle_delivery_distance = models.DecimalField(help_text="Set distance in miles", default=2.0, decimal_places=2, max_digits=6, blank=False)
    motorcycle_radius = models.DecimalField(help_text="Set radius in miles", default=7.0, decimal_places=2, max_digits=6, blank=False)
    motorcycle_delivery_distance = models.DecimalField(help_text="Set distance in miles", default=8.0, decimal_places=2, max_digits=6, blank=False)
    car_radius = models.DecimalField(help_text="Set radius in miles", default=7.0, decimal_places=2, max_digits=6, blank=False)
    car_delivery_distance = models.DecimalField(help_text="Set distance in miles", default=8.0, decimal_places=2, max_digits=6, blank=False)

    def __str__(self):
        return "#{} Bicycle {} Motorcycle {} Car {}".format(self.id, self.bicycle_radius, self.motorcycle_radius, self.car_radius)

class DriverLocation(models.Model):
    driver = models.ForeignKey(Driver, null=True, related_name='locations', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    point = models.PointField(blank=True, null=True)

    def __str__(self):
        return "#{} Driver {} Timestamp {} Latitude {} Longitude {}".format(self.id, self.driver, self.timestamp, self.latitude, self.longitude)


# delivery_route = models.ForeignKey(DeliveryRoute, on_delete=models.CASCADE, blank=True, null=True, related_name='order_delivery_route')
#     delivery_partner_driver = models.ForeignKey(DeliveryPartnerDriver, related_name='order_delivery_partner_drivers', on_delete=models.PROTECT, blank=True, null=True)
#     delivery_partner_job = models.ForeignKey(DeliveryPartnerJob, related_name='order_delivery_partner_drivers', on_delete=models.PROTECT, blank=True, null=True)
