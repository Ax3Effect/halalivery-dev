from django.contrib.gis.db import models
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.utils.encoding import python_2_unicode_compatible
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from .static import VENDOR_TYPE

from halalivery.vendors import VendorType
from halalivery.drivers import InsuranceType, TransportType
from halalivery.static import *
import requests
import json
import os
import stripe

from operator import attrgetter

from django.contrib.gis.geos import Point


@python_2_unicode_compatible
class User(AbstractUser):
    onesignal_token = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return "{} - {} - {}".format(self.username, self.first_name, self.last_name)

    def send_notification(self, message):
        try:
            self.customer
            self.customer.send_notification(message)
            return True
        except Customer.DoesNotExist:
            pass

        try:
            self.driver
            self.driver.send_notification(message)
            return True
        except Driver.DoesNotExist:
            pass

        try:
            self.vendor
            self.vendor.send_notification(message)
            return True
        except Vendor.DoesNotExist:
            pass

        return False


class Address(models.Model):
    address_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120, blank=True, null=True)
    company_name = models.CharField(max_length=120, blank=True, null=True)
    street_address_1 = models.CharField(max_length=120, blank=False, null=True)
    street_address_2 = models.CharField(max_length=120, blank=True, null=True)
    postcode = models.CharField(max_length=10, blank=False)
    city = models.CharField(max_length=50, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    point = models.PointField(blank=True, null=True)
    delivery_instructions = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return 'Address #{} {} {} - {} - {} - {} - {}'.format(self.id, self.first_name, self.last_name, self.street_address_1, self.street_address_2, self.postcode, self.city)

    def save(self, *args, **kwargs):
        latitude = 0.0
        longitude = 0.0

        if self.postcode is not None or self.postcode is not "":
            r = requests.get("https://api.postcodes.io/postcodes/{}".format(self.postcode))
            r_json = r.json()
            if r_json["status"] == 404:
                raise ValidationError('Postcode not found')

            latitude = r_json["result"]["latitude"]
            longitude = r_json["result"]["longitude"]

        self.latitude = latitude
        self.longitude = longitude
        self.point = Point(longitude, latitude)
        super().save(*args, **kwargs)


class PaymentToken(models.Model):
    token = models.CharField(max_length=100, unique=True, blank=False)
    provider = models.CharField(max_length=20, blank=False)
    payment_method = models.CharField(max_length=20, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    masked_number = models.IntegerField()
    payment_type = models.CharField(max_length=10, blank=True)
    expiration_date = models.CharField(max_length=10, blank=True)
    customer_id = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return "Payment Token {}".format(self.id)


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    address = models.ManyToManyField(Address, blank=True, related_name='customer_address')
    payment_token = models.ManyToManyField(PaymentToken, related_name='payment_token', blank=True)
    avatar = models.CharField(max_length=500, blank=True)

    def send_notification(self, message):
        if self.user.onesignal_token:
            header = {"Content-Type": "application/json; charset=utf-8",
                      "Authorization": "Basic " + ONESIGNAL_ORDERAPP_API_KEY}

            payload = {"app_id": ONESIGNAL_ORDERAPP_APP_ID, "include_player_ids": [
                "{}".format(self.user.onesignal_token)], "contents": {"en": "{}".format(message)}}

            req = requests.post("https://onesignal.com/api/v1/notifications",
                                headers=header, data=json.dumps(payload))
            return True
        else:
            return False

    def __str__(self):
        return 'Customer #{}'.format(self.id)
    
    def get_email(self):
        return self.user.email if self.user else ''

    # def __str__(self):
    #     return "Customer #{} {} {}".format(self.id, self.user.first_name, self.user.last_name)


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver')
    dob = models.DateField(null=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, blank=True, null=True)
    transport_type = models.CharField(max_length=50, choices=TransportType.CHOICES, blank=False, null=True)
    online = models.BooleanField(blank=True, default=False)
    # location = models.ManyToManyField(Location, related_name='driver_location', blank=True)
    avatar = models.CharField(max_length=500, blank=True)
    stripe_connect_id = models.CharField(max_length=50, null=True, blank=True)
    insurance_type = models.CharField(choices=InsuranceType.CHOICES, null=True, max_length=50)
    zego_registration_url = models.CharField(max_length=500, null=True, blank=True)

    def send_notification(self, message):
        if self.user.onesignal_token:
            header = {"Content-Type": "application/json; charset=utf-8",
                      "Authorization": "Basic " + ONESIGNAL_DRIVERAPP_API_KEY}

            payload = {"app_id": ONESIGNAL_DRIVERAPP_APP_ID, "include_player_ids": [
                "{}".format(self.user.onesignal_token)], "contents": {"en": "{}".format(message)}}

            req = requests.post("https://onesignal.com/api/v1/notifications",
                                headers=header, data=json.dumps(payload))
            return True
        else:
            return False

    # def __str__(self):
    #     return 'Driver #{} {}'.format(self.id,self.user.get_full_name()) if self.user.get_full_name() != '' else 'Driver #{}'.format(self.id)
    def __str__(self):
        return 'Driver #{}'.format(self.id)

    def delete(self, *args, **kwargs):
        if self.stripe_connect_id != '':
            stripe.api_key = STRIPE_API_KEY
            account = stripe.Account.retrieve("{}".format(self.stripe_connect_id))
            account.delete()
        super().delete(*args, **kwargs)
    
    def get_last_location(self):
        return max(self.locations.all(), default=None, key=attrgetter('pk'))

    def get_active_order(self):
        return max(self.order_drivers.filter(status__range=[2, 5]), default=None, key=attrgetter('pk'))
    

def get_upload_path(instance, filename):
    return os.path.join('vendor', str(instance.id), 'logo', filename)

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor')
    vendor_name = models.CharField(max_length=100)
    vendor_type = models.CharField(max_length=32, choices=VendorType.CHOICES, default=VendorType.GROCERY)
    companyhouse_number = models.CharField(max_length=10, null=True, blank=True)
    halalivery_exclusive = models.NullBooleanField(default=False, blank=True)
    hmc_approved = models.NullBooleanField(default=False, blank=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, null=True)
    legal_entity_first_name = models.CharField(max_length=20, blank=True)
    legal_entity_last_name = models.CharField(max_length=20, blank=True)
    legal_entity_dob = models.DateField(null=True, blank=True)
    legal_entity_phone = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to=get_upload_path, blank=True)
    stripe_connect_id = models.CharField(max_length=50, null=True, blank=True)

    def send_notification(self, message):
        if self.user.onesignal_token:
            test = False
            if test:
                header = {"Content-Type": "application/json; charset=utf-8",
                          "Authorization": "Basic " + ONESIGNAL_ORDERAPP_API_KEY}

                payload = {"app_id": ONESIGNAL_ORDERAPP_APP_ID, "include_player_ids": [
                    "{}".format(self.user.onesignal_token)], "contents": {"en": "{}".format(message)}}

                req = requests.post("https://onesignal.com/api/v1/notifications",
                                    headers=header, data=json.dumps(payload))
                return True
            else:
                header = {"Content-Type": "application/json; charset=utf-8",
                          "Authorization": "Basic " + ONESIGNAL_VENDORAPP_API_KEY}

                payload = {"app_id": ONESIGNAL_VENDORAPP_APP_ID, "include_player_ids": [
                    "{}".format(self.user.onesignal_token)], "contents": {"en": "{}".format(message)}}

                req = requests.post("https://onesignal.com/api/v1/notifications",
                                    headers=header, data=json.dumps(payload))
                #print(req.json())
                return True
        else:
            return False

    def marketplace(self):
        if self.vendor_type == VendorType.RESTAURANT:
            return self.restaurant
        elif self.vendor_type == VendorType.GROCERY:
            return self.grocery

    def __str__(self):
        return self.vendor_name

    def delete(self, *args, **kwargs):
        if self.stripe_connect_id != '':
            stripe.api_key = STRIPE_API_KEY
            account = stripe.Account.retrieve("{}".format(self.stripe_connect_id))
            account.delete()
        super().delete(*args, **kwargs)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
