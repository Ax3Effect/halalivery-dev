from django.dispatch import Signal
from django.dispatch import receiver

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from decimal import Decimal
import requests
from halalivery.static import SLACK_ORDER_WEBHOOK_URL

driver_zego = Signal(providing_args=["driver"])
driver_credentials = Signal(providing_args=["driver", "username", "password"])
driver_credentials_with_zego = Signal(providing_args=["driver","username", "password"])

@receiver(driver_zego)
def driver_zego_signal(sender, driver, **kwargs):
    email = driver.user.email
    if email:
        subject = "Halalivery Rider - Important"

        merge_data = {
            'zego_url': driver.zego_registration_url,
            'firstname': driver.user.first_name,
            'support_email': 'info@halalivery.co.uk'
        }
        text_body = render_to_string("driver_zego_url.html", merge_data)
        msg = EmailMultiAlternatives(subject=subject, from_email="info@halalivery.co.uk",
                                     to=["{}".format(email)], body=text_body)
        msg.attach_alternative(text_body, "text/html")
        msg.send()

@receiver(driver_credentials)
def driver_credentials_signal(sender, driver, username, password, **kwargs):
    email = driver.user.email
    driver_id = driver.id
    if email:
        subject = "Halalivery Rider - Important"

        merge_data = {
            'driver_id': driver_id,
            'username': username,
            'password': password,
            'support_email': 'info@halalivery.co.uk'
        }
        text_body = render_to_string("driver_credentials.html", merge_data)
        msg = EmailMultiAlternatives(subject=subject, from_email="info@halalivery.co.uk",
                                     to=["{}".format(email)], body=text_body)
        msg.attach_alternative(text_body, "text/html")
        msg.send()
    
@receiver(driver_credentials_with_zego)
def driver_credentials_with_zego_signal(sender, driver, username, password, **kwargs):
    email = driver.user.email
    driver_id = driver.id
    if email:
        subject = "Halalivery Rider - Important"

        merge_data = {
            'driver_id': driver_id,
            'username': username,
            'password': password,
            'zego_url': driver.zego_registration_url,
            'support_email': 'info@halalivery.co.uk'
        }
        text_body = render_to_string("driver_credentials_with_zego.html", merge_data)
        msg = EmailMultiAlternatives(subject=subject, from_email="info@halalivery.co.uk",
                                     to=["{}".format(email)], body=text_body)
        msg.attach_alternative(text_body, "text/html")
        msg.send()