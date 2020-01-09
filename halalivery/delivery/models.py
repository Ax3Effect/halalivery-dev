from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField

from halalivery.order.models import Order
from halalivery.delivery import RouteType

class DeliveryRoute(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True, related_name='delivery_route')
    timestamp = models.DateTimeField(auto_now_add=True)
    created_at = models.DateField(auto_now=True)
    latitude_from = models.FloatField(blank=True)
    longitude_from = models.FloatField(blank=True)
    latitude_to = models.FloatField(blank=True)
    longitude_to = models.FloatField(blank=True)
    origin_addresses = models.CharField(blank=True, max_length=300)
    destination_addresses = models.CharField(blank=True, max_length=300)
    distance = models.DecimalField(blank=True, default=0.0, decimal_places=2, max_digits=6)
    distance_in_miles = models.DecimalField(blank=True, default=0.0, decimal_places=2, max_digits=6)
    distance_text = models.CharField(blank=True, max_length=50)
    duration = models.CharField(blank=True, max_length=50)
    duration_text = models.CharField(blank=True, max_length=50)
    driver_payout = models.DecimalField(blank=True, default=0.0, decimal_places=2, max_digits=6)
    route_type = models.CharField(choices=RouteType.CHOICES, blank=True, max_length=50)
    gateway_response = JSONField(default=dict, blank=True)
    can_bicycle_deliver = models.BooleanField(default=False, blank=True)
    can_motorcycle_deliver = models.BooleanField(default=False, blank=True)
    can_car_deliver = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return "#{} Distance {} Driver payout {}".format(self.id, self.distance, self.driver_payout)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    def can_deliver(self, distance=None):
        return self.distance <= distance

class DeliveryPartnerJob(models.Model):
    order = models.ForeignKey(Order,  on_delete=models.CASCADE, blank=True, null=True, related_name='delivery_partner_jobs')
    job_id = models.IntegerField(default=0, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    pickup_at = JSONField(blank=True, null=True)
    dropoff_at = JSONField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    origin_comment = models.CharField(max_length=200, blank=True, null=True)
    destination_comment = models.CharField(max_length=200, blank=True, null=True)
    job_reference = models.CharField(max_length=200, blank=True, null=True)
    current_delivery = JSONField(blank=True, null=True)
    transport_type = models.CharField(max_length=200, blank=True, null=True)
    packageType = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return "Order #{} - Job #{} - Package type {} - Created {}".format(self.order and self.order.id, self.job_id, self.packageType, self.created_at)

class DeliveryPartnerDriver(models.Model):
    job = models.ForeignKey(DeliveryPartnerJob, on_delete=models.CASCADE, blank=True, null=True, related_name='driver')
    status = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    firstname = models.CharField(max_length=50, blank=True, null=True)
    lastname = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    picture_path_imgix = models.CharField(max_length=200, blank=True, null=True)
    transport_type = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    point = models.PointField(blank=True, null=True)

    def __str__(self):
        return "#{} Job #{} Timestamp {} Latitude {} Longitude {}".format(self.id, self.job, self.timestamp, self.latitude, self.longitude)