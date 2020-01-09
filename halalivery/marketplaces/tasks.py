from celery import shared_task

import requests
import os
from halalivery.static import SLACK_CRON_JOBS_WEBHOOK_URL, GOOGLE_MAPS_API_KEY
from halalivery.order.models import Order
from halalivery.users.models import Customer, Vendor, Driver
from halalivery.drivers.models import DriverPayout
from halalivery.delivery.models import DeliveryRoute
from halalivery.delivery import RouteType

from halalivery.static import SLACK_ORDER_WEBHOOK_URL, SLACK_ORDER_ISSUES_WEBHOOK_URL
from . import signals

from halalivery.helpers import yards_to_miles

from halalivery.drivers.models import DriverOrderVisibility


# Google maps api
import googlemaps
from datetime import datetime

from decimal import Decimal

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.utils import timezone

import newrelic.agent
import sys

from sentry_sdk import capture_exception

@shared_task
def order_placed_task(order_id):
    order = Order.objects.get(id=order_id)
    order.vendor.user.send_notification("New order: #{}".format(order.id))

    email = order.customer.user.email
    if email:
        subject = "Your order #{} from Halalivery".format(order.id)

        order_items = order.return_items()

        merge_data = {
            'order': order,
            'order_id': order.id,
            'order_total': order.total,
            'order_items': order_items,
            'first_name': order.customer.user.first_name,
            'last_name': order.customer.user.last_name,
            'customer_address': order.customer.address,
            'vendor_name': order.vendor.vendor_name,
            'vendor_address': order.vendor.address,
            'subtotal': order.subtotal
        }
        text_body = render_to_string("email_order.html", merge_data)
        msg = EmailMultiAlternatives(subject=subject, from_email="info@halalivery.co.uk",
                                     to=["{}".format(email)], body=text_body)
        msg.attach_alternative(text_body, "text/html")
        # msg.attach_alternative(html_body, "text/html")
        msg.send()

    # customer.send_notification("Your order #{} has been placed!".format(order.id))

@shared_task
def started_preparation_notification(order_id):
    order = Order.objects.get(id=order_id)
    if order:
        order.driver.send_notification("Order #{} from {} is available".format(
            order.id, order.vendor.marketplace()))
    else:
        pass

@shared_task
def order_accepted_notification(order_id):
    order = Order.objects.get(id=order_id)
    order.customer.send_notification("Your Order #{} was accepted by {}! ☺️".format(order.id, order.vendor.marketplace()))

@shared_task
def order_ready_for_self_pickup_task(order_id):
    order = Order.objects.get(id=order_id)
    try:
        order.customer.send_notification(
            "Order #{} from {} is ready for the self pickup!".format(
                order.id, order.vendor.marketplace()))
    except Exception:
        pass

@shared_task
def order_ready_for_pickup_task(order_id):
    order = Order.objects.get(id=order_id)
    try:
        order.driver.send_notification(
            "Order #{} from {} is available for pickup".format(
                order.id, order.vendor.marketplace()))
    except Exception:
        pass

@shared_task
def order_placed_slack_task(order_id, vendor_id, customer_id):
    order = Order.objects.get(id=order_id)
    customer = Customer.objects.get(id=customer_id)
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "Hurray new order has been *recieved!*",
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nTotal: *£{}*".format(order.status, customer.user.first_name, customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, order.total),
                    "mrkdwn_in": [
                            "text",
                            "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def order_available_task(order_id, driver_id):
    print("Order available for drivers to accept")
    order = Order.objects.get(id=order_id)
    driver = Driver.objects.get(id=driver_id)
    if driver: 
        driver.send_notification("New order #{} from {} is available!".format(
            order.id, order.vendor.marketplace()))

@shared_task
def order_rejected_task(order_id):
    order = Order.objects.get(id=order_id)
    try:
        order.customer.send_notification("Your order was rejected by {}.".format(order.vendor.vendor_name))
        requests.post(
            url=SLACK_ORDER_ISSUES_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": "Order #{}".format(order.id),
                        "pretext": "{} has *rejected* order #{}".format(order.vendor, order.id),
                        "text": "Please contact {} if required!\nVendor phone: {}\nDelivery address: *{}*\nTotal: *£{}*".format(order.vendor.vendor_name, order.vendor.address.phone, order.delivery_address, order.total),
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )
    except Exception:
        pass

@shared_task
def driver_collected_task(order_id):
    order = Order.objects.get(id=order_id)
    order.customer.send_notification(
        "Driver has collected your order #{} and is on the way. 🤗 🎉".format(order.id))

    customer = Customer.objects.get(id=order.customer.id)
    driver_first_name = ''
    driver_last_name = ''
    if order.driver:
        driver = Driver.objects.get(id=order.driver.id)
        driver_first_name = driver.user.first_name
        driver_last_name = driver.user.last_name
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "Driver {} {} has *collected* an order!".format(driver_first_name, driver_last_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nDriver:*{} {}*\nTotal: *£{}*".format(order.status, customer.user.first_name, customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, driver_first_name, driver_last_name, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def driver_delivered_task(order_id):
    order = Order.objects.get(id=order_id)
    customer = Customer.objects.get(id=order.customer.id)
    driver_first_name = ''
    driver_last_name = ''
    if order.driver:
        driver = Driver.objects.get(id=order.driver.id)
        driver_first_name = driver.user.first_name
        driver_last_name = driver.user.last_name
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "Driver {} {} has *delivered* an order!".format(driver_first_name, driver_last_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nDriver:*{} {}*\nTotal: *£{}*".format(order.status, customer.user.first_name, customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, driver_first_name, driver_last_name, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def driver_accepted_task(order_id):
    order = Order.objects.get(id=order_id)
    customer = Customer.objects.get(id=order.customer.id)
    driver_first_name = ''
    driver_last_name = ''
    if order.driver:
        driver = Driver.objects.get(id=order.driver.id)
        driver_first_name = driver.user.first_name
        driver_last_name = driver.user.last_name
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "Driver {} {} has *accepted* an order!".format(driver_first_name, driver_last_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nDriver:*{} {}*\nTotal: *£{}*".format(order.status, customer.user.first_name, customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, driver_first_name, driver_last_name, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def vendor_delivery_halalivery_task(order_id, vendor_id):
    order = Order.objects.get(id=order_id)
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "*{}* selected *Halalivery delivery*!".format(order.vendor.vendor_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nTotal: *£{}*".format(order.status, order.customer.user.first_name, order.customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def vendor_delivery_own_task(order_id, vendor_id):
    order = Order.objects.get(id=order_id)
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "*{}* selected *Own delivery*!".format(order.vendor.vendor_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nTotal: *£{}*".format(order.status, order.customer.user.first_name, order.customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def vendor_prepared_task(order_id, vendor_id):
    order = Order.objects.get(id=order_id)
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "*{}* has *prepared* the order!".format(order.vendor.vendor_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nTotal: *£{}*".format(order.status, order.customer.user.first_name, order.customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def vendor_delivered_task(order_id, vendor_id):
    order = Order.objects.get(id=order_id)
    requests.post(
        url=SLACK_ORDER_WEBHOOK_URL,
        json={
            "attachments": [
                {
                    "title": "Order #{}".format(order.id),
                    "pretext": "*{}* has *delivered* the order!".format(order.vendor.vendor_name),
                    "text": "Order status: {}\nFull Name: *{} {}*\nDelivery type: *{}*\nFrom: *{}*\nVendor type: *{}*\nVendor phone: *{}*\nDelivery address: *{}*\nTotal: *£{}*".format(order.status, order.customer.user.first_name, order.customer.user.last_name, order.delivery_type, order.vendor.vendor_name, order.vendor.vendor_type, order.vendor.address.phone, order.delivery_address, order.total),
                    "mrkdwn_in": [
                        "text",
                        "pretext"
                    ]
                }
            ]
        }
    )

@shared_task
def check_for_drivers_task():
    orders = Order.objects.filter(status__in=[2, 3], delivery_type=0, driver__isnull=True)
    order_ids = ""
    if orders.count() > 0:
        for order in orders:
            order_ids += "{},".format(order.id)

        requests.post(
            url=SLACK_ORDER_ISSUES_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": "Orders #{}".format(order_ids),
                        "pretext": "Orders *{}* don't have any drivers to deliver!".format(order_ids),
                        "text": "Please assign a driver to the listed orders!",
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )

@shared_task
def send_notification_to_drivers_around_task():
    # TO DO SEND ORDER TO DRIVERS IN THE RANGE
    # drivers = Driver.objects.filter(online=True)
    orders = Order.objects.filter(status__in=[2, 3], driver__isnull=True)
    #order
    #driver_order_visibility = DriverOrderVisibility.objects.all().last()
    # if orders:
    #     driver_order_visibility = DriverOrderVisibility.objects.all().last()
    #     drivers = Driver.objects.filter(online=True)
    #     in_range = 
        # for order in orders:
        #     for driver in drivers:
        #         last_location = driver.get_last_location()
        #         active_order = driver.get_active_order()
        #         if not active_orders:
        #             order.


                
            #delivery_distance = DeliveryRoute.objects.get(order=order)

            #print(delivery_distance.can_deliver(distance=driver_order_visibility.))
            # If cyclists can deliver:


            #drivers_around_the_order = Driver.objects.filter(online=True)
            # online_drivers_without_order = Driver.objects.filter(online=True)
            # #drivers_in_area = 1
            # for online_driver_without_order in online_drivers_without_order:
            #     print(online_driver_without_order.get_active_order())

@shared_task
def send_notification_to_drivers_online_task():
    orders = Order.objects.filter(status__in=[2, 3], delivery_type=0, driver__isnull=True)
    online_drivers = Driver.objects.filter(online=True)
    if orders:
        for order in orders:
            if online_drivers:
                for driver in online_drivers:
                    if not driver.get_active_order():
                        signals.order_available.send(sender=None, order=order, driver=driver)
# def update_order_with_payout(order_id: int, delivery_route_id: int):
#     order = Order.objects.get(id=order_id)
#     delivery_route = DeliveryRoute.objects.get(id=delivery_route_id)
#     order.delivery_route = delivery_route
#     order.save()

@shared_task
def calculate_distance(order_id: int, customer_id: int):
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    order = Order.objects.get(id=order_id)
    if not order.delivery_address:
        return
    driver_payout = DriverPayout.objects.all().last()
    driver_order_visibility = DriverOrderVisibility.objects.all().last()
    lat_to = order.delivery_address.latitude
    long_to = order.delivery_address.longitude

    lat_from = order.vendor.address.latitude
    long_from = order.vendor.address.longitude

    try:
        directions_result = gmaps.distance_matrix(origins=(lat_from, long_from), destinations=(
            lat_to, long_to), mode='driving', units='imperial', departure_time=timezone.localtime(timezone.now()), traffic_model='best_guess')

        if directions_result and directions_result['status'] == 'OK':
            destination_address = directions_result['destination_addresses'][0]
            origin_address = directions_result['origin_addresses'][0]
            distance_text = directions_result['rows'][0]['elements'][0]['distance']['text']
            distance = Decimal(directions_result['rows'][0]['elements'][0]['distance']['value'])

            duration = Decimal(directions_result['rows'][0]['elements'][0]['duration']['value'])
            duration_text = directions_result['rows'][0]['elements'][0]['duration']['text']

            payout = driver_payout.per_mile * (Decimal(distance) * Decimal('0.00056818'))
            payout = round(payout, 2)

            if payout < driver_payout.minimum:
                payout = driver_payout.minimum
            elif payout > driver_payout.maximum:
                payout = driver_payout.maximum

            distance_in_miles = yards_to_miles(yards=distance)

            can_bicycle_deliver = driver_order_visibility.bicycle_delivery_distance >= distance_in_miles
            can_motorcycle_deliver = driver_order_visibility.motorcycle_delivery_distance >= distance_in_miles
            can_car_deliver = driver_order_visibility.car_delivery_distance >= distance_in_miles

            delivery_route, _ = DeliveryRoute.objects.get_or_create(
                order=order,
                latitude_from=lat_from,
                longitude_from=long_from,
                latitude_to=lat_to,
                longitude_to=long_to,
                origin_addresses=origin_address,
                destination_addresses=destination_address,
                distance=distance,
                distance_in_miles=distance_in_miles,
                distance_text=distance_text,
                duration=duration,
                duration_text=duration_text,
                driver_payout=payout,
                can_bicycle_deliver=can_bicycle_deliver,
                can_motorcycle_deliver=can_motorcycle_deliver,
                can_car_deliver=can_car_deliver,
                route_type=RouteType.DRIVING,
                gateway_response=directions_result
            )

            # order.delivery_route = delivery_route

            #update_order_with_payout(order_id=order.id, delivery_route_id=delivery_route.id)

    except Exception as e:
        capture_exception(e)
        exc_info = sys.exc_info()
        newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
        requests.post(
            url=SLACK_ORDER_ISSUES_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": "Order #{}".format(order.id),
                        "pretext": "Order *{}* doesn't a have correct driver payout!".format(order.id),
                        "text": "Please check the distance calculation in the DeliveryRoute of the order.",
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )






    # update_order_with_payout(order_id=order.id, customer_id=customer_id, payout_id=)
        # {'destination_addresses': ['119 Derby Rd, Nottingham NG7 1LS, UK'], 'origin_addresses': ['University of Nottingham: Jubilee Campus, Computer Science and Dearing Buildings, Nottingham NG8 1AW, UK'], 'rows': [{'elements': [{'distance': {'text': '2.2 km', 'value': 2237}, 'duration': {'text': '6 mins', 'value': 367}, 'status': 'OK'}]}], 'status': 'OK'}
        # print(directions_result['rows'][0][0]['distance'])

        # requests.post(
        #     url=SLACK_ORDER_WEBHOOK_URL,
        #     json={
        #         "attachments": [
        #             {
        #                 "title": "Orders #{}".format(1),
        #                 "pretext": "Orders *{}* don't have any drivers to deliver!".format(1),
        #                 "text": "{} {} {} {} {} {}".format(destination_address, origin_address, distance_text, duration_text, distance, payout),
        #                 "mrkdwn_in": [
        #                     "text",
        #                     "pretext"
        #                 ]
        #             }
        #         ]
        #     }
        # )
