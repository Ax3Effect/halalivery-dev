from django.dispatch import Signal
from django.dispatch import receiver

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from decimal import Decimal
import requests
from halalivery.static import SLACK_ORDER_WEBHOOK_URL


from .tasks import *

order_placed = Signal(providing_args=["order"])
order_placed_slack = Signal(providing_args=["order", "vendor", "customer"])
order_accepted = Signal(providing_args=["order"])
order_available = Signal(providing_args=["order", "driver"])
order_rejected = Signal(providing_args=["order"])
order_started_preparing =  Signal(providing_args=["order"])
order_ready_for_pickup = Signal(providing_args=["order"])
order_ready_for_self_pickup = Signal(providing_args=["order"])
order_delivered = Signal(providing_args=["order"])
driver_collected = Signal(providing_args=["order"])
driver_accepted = Signal(providing_args=["order", "driver"])
driver_rejected = Signal(providing_args=["order", "driver"])
vendor_delivery_halalivery = Signal(providing_args=["order", "vendor"])
vendor_delivery_own = Signal(providing_args=["order", "vendor"])
vendor_prepared_order = Signal(providing_args=["order", "vendor"])
calculate_driver_payout = Signal(providing_args=["order", "customer"])
vendor_delivered = Signal(providing_args=["order", "vendor"])


@receiver(order_placed)
def order_placed_signal(sender, order, **kwargs):
    print("Vendor notified")
    order_placed_task.delay(order_id=order.id)

@receiver(order_placed_slack)
def order_placed_slack_signal(sender, order, vendor, customer, **kwargs):
    print("Slack notified")
    #Post to slack
    order_placed_slack_task.delay(order_id=order.id, vendor_id=vendor.id, customer_id=customer.id)

    #customer.send_notification("Your order #{} has been placed!".format(order.id))

@receiver(order_accepted)
def order_accepted_signal(sender, order, **kwargs):
    print("Order accepted")
    order_accepted_notification.delay(order_id=order.id)

@receiver(order_available)
def order_available_signal(sender, order, driver, **kwargs):
    print("Order available {}".format(order.id))
    order_available_task.delay(order_id=order.id, driver_id=driver.id)

@receiver(order_rejected)
def order_rejected_signal(sender, order, **kwargs):
    print("Order rejected")
    order_rejected_task.delay(order_id=order.id)

@receiver(order_started_preparing)
def order_started_preparing_signal(sender, order, **kwargs):
    print("Order started preparing")
    started_preparation_notification.delay(order_id=order.id)

@receiver(order_ready_for_pickup)
def order_ready_for_pickup_signal(sender, order, **kwargs):
    print("Order ready for pickup")
    order_ready_for_pickup_task.delay(order_id=order.id)

@receiver(order_ready_for_self_pickup)
def order_ready_for_self_pickup_signal(sender, order, **kwargs):
    print("Order ready for self pickup")
    order_ready_for_self_pickup_task.delay(order_id=order.id)

# Driver signals
@receiver(driver_collected)
def driver_collected_signal(sender, order, **kwargs):
    driver_collected_task.delay(order_id=order.id)

@receiver(order_delivered)
def order_delivered_signal(sender, order, **kwargs):
    print("Order delivered")
    driver_delivered_task.delay(order_id=order.id)

@receiver(driver_accepted)
def driver_accepted_signal(sender, order, **kwargs):
    print("Order accepted by driver")
    driver_accepted_task.delay(order_id=order.id)

@receiver(driver_rejected)
def driver_rejected_signal(sender, order, **kwargs):
    print("Driver rejected")

# Vendor signals
@receiver(vendor_delivery_halalivery)
def vendor_delivery_halalivery_signal(sender, order, vendor, **kwargs):
    print('Vendor delivery halalivery')
    vendor_delivery_halalivery_task.delay(order_id=order.id, vendor_id=vendor.id)
    #order.customer.send_notification(
    #    "{}'s driver has collected your order #{} and is on the way.".format(order.vendor.marketplace(), order.id))

@receiver(vendor_delivery_own)
def vendor_delivery_own_signal(sender, order, vendor, **kwargs):
    print("Vendor delivery own")
    vendor_delivery_own_task.delay(order_id=order.id, vendor_id=vendor.id)

@receiver(vendor_prepared_order)
def vendor_prepared_order_signal(sender, order, vendor, **kwargs):
    print("Vendor prepared order")
    vendor_prepared_task.delay(order_id=order.id, vendor_id=vendor.id)

@receiver(vendor_delivered)
def vendor_delivered_signal(sender, order, vendor, **kwargs):
    print("Vendor delivered")
    vendor_delivered_task.delay(order_id=order.id, vendor_id=vendor.id)

@receiver(calculate_driver_payout)
def calculate_driver_payout_signal(sender, order, customer, **kwargs):
    print("Calculate driver payout.")
    calculate_distance.delay(order_id=order.id, customer_id=customer.id)