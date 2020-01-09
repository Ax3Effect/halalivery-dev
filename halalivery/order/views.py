# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import requests
import datetime as dt
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils.crypto import get_random_string
from django.db.models import Q, F
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from ..core.utils.taxes import zero_money

# Time libs
from django.utils import timezone
from decimal import Decimal

# Error catching
import sys
import traceback
import newrelic.agent
from sentry_sdk import capture_exception


from halalivery.marketplaces.models import Restaurant, Grocery, MarketplaceVisibillity
from halalivery.basket.models import Basket, BasketItemMod, BasketItem
from halalivery.basket.serializers import BasketSerializer
from halalivery.order.models import Order, OrderItem, OrderItemMod
from halalivery.order import OrderStatus, OrderEvents
from halalivery.menu.models import MenuItem, MenuItemOption, Menu, MenuCategory
from halalivery.delivery import DeliveryType
from .serializers import OrderSerializer
from halalivery.users.models import Customer, Address, PaymentToken, Vendor
from halalivery.users.permissions import IsAuthenticatedCustomer

# Payments
from halalivery.payment import ChargeStatus, PaymentError
from halalivery.payment.models import Payment
from halalivery.payment.utils import (
    create_payment, create_payment_information, gateway_process_payment, gateway_authorize)
from halalivery.payment import get_payment_gateway
from halalivery.payment.models import Transfer

from halalivery.partner_discounts.models import PartnerDiscount

from halalivery.coupons.models import Coupon
from halalivery.coupons.utils import get_voucher_for_cart, increase_voucher_usage
from halalivery.helpers import get_client_ip
from halalivery.marketplaces.models import OperatingTime

# Postgis
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance

from halalivery.marketplaces import signals

from halalivery.drivers.gateways.stuart import StuartClient

PAYMENT_CHOICES = [
    (k, v) for k, v in settings.CHECKOUT_PAYMENT_GATEWAYS.items()]

# Create your views here.


@permission_classes([IsAuthenticatedCustomer, ])
class CreateOrderView(APIView):
    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        basket = get_object_or_404(Basket, customer=customer)

        serializer = BasketSerializer(basket)
        vendor_id = serializer.data.get('vendor_id', 0)
        delivery_fee = serializer.data.get('delivery_fee', Decimal(0))
        delivery_type = serializer.data.get('delivery_type', DeliveryType.DELIVERY)
        driver_tip = serializer.data.get('driver_tip', Decimal(0))
        total = serializer.data.get('total', Decimal(0))
        subtotal = serializer.data.get('subtotal', Decimal(0))
        customer_note = serializer.data.get('note', '')
        discount_amount = serializer.data.get('discount_amount', Decimal(0))
        surcharge = serializer.data.get('surcharge', Decimal(0))

        vendor = get_object_or_404(Vendor, id=vendor_id)

        if not vendor.marketplace().is_available():
            return Response({"error": "{} is no longer available.".format(vendor)}, status=status.HTTP_404_NOT_FOUND)

        if delivery_type == DeliveryType.SELF_PICKUP:
            order = Order(customer=customer, vendor=vendor, driver_tip=driver_tip, total=total, subtotal=subtotal, surcharge=surcharge,
                          prep_time=vendor.marketplace().prep_time.time(), delivery_type=delivery_type, customer_note=customer_note, user_email=customer.get_email())
        else:
            if not basket.address:
                return Response({"error": "Please provide a delivery address"},
                                status=status.HTTP_400_BAD_REQUEST)
            customer_address = get_object_or_404(customer.address, id=basket.address.id)
            order = Order(customer=customer, vendor=vendor, driver_tip=driver_tip, delivery_fee=delivery_fee, total=total, subtotal=subtotal, surcharge=surcharge,
                          prep_time=vendor.marketplace().prep_time.time(), delivery_address=customer_address, billing_address=customer_address, customer_note=customer_note, user_email=customer.get_email())

        order.confirmation_code = get_random_string(
            length=5, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

        voucher = basket.voucher

        # If customer already has orders otherwise don't apply
        customer_has_orders = Order.objects.filter(customer=customer).exists()
        partner_discount = basket.partner_discount

        if voucher:
            if customer_has_orders and not voucher.expired() and not voucher.is_redeemed and not voucher.redeemed_by_user(customer):
                voucher.redeem(customer)
                order.voucher = voucher
                order.discount_amount = discount_amount
            else:
                return Response({'error': 'Voucher code is not applicable.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if not customer_has_orders or partner_discount:
            order.discount_amount = discount_amount
            order.partner_discount_is_applied = True

        order.save()
        basket_items = basket.items.all()
        for basket_item in basket_items:
            order_item = OrderItem(order=order, name=basket_item.item.name,
                                   quantity=basket_item.quantity, price=basket_item.item.price)
            order_item.save()
            item_mods = basket_item.mods.all()
            for item_mod in item_mods:
                # a.mods.add(y)
                order_item_mod = OrderItemMod(
                    order_line=order_item, name=item_mod.mod.name, quantity=item_mod.quantity)
                order_item_mod.save()

        order.time_placed = timezone.localtime(timezone.now())
        order.save()

        basket.delete()

        order.events.create(type=OrderEvents.PLACED.value)

        order_serializer = OrderSerializer(order)
        return Response(order_serializer.data)

@permission_classes([IsAuthenticatedCustomer, ])
class OrderPaymentView(APIView):
    def post(self, request, format=None):
        customer = get_object_or_404(Customer.objects.prefetch_related('payment_token'), user=request.user)
        try:
            json_data = json.loads(request.body)
            order_id = json_data.pop('order_id', -1)
            if order_id > 0:
                order = get_object_or_404(Order, id=order_id, customer=customer)

                payment_token = json_data.pop('payment_token', None)
                payment_token_id = json_data.pop('payment_token_id', None)
                gateway = json_data.pop('provider', 'stripe')

                if payment_token:
                    payment_gateway, connection_params = get_payment_gateway(gateway_name=gateway)
                    extra_data = {'customer_user_agent': request.META.get('HTTP_USER_AGENT')}
                    with transaction.atomic():
                        payment = create_payment(
                            gateway=gateway,
                            currency=settings.DEFAULT_CURRENCY,
                            email=order.user_email,
                            billing_address=order.billing_address,
                            customer_ip_address=get_client_ip(request),
                            payment_token=payment_token,
                            total=order.total,
                            order=order,
                            extra_data=extra_data)

                        if (order.is_fully_paid()
                                or payment.charge_status == ChargeStatus.FULLY_REFUNDED or order.is_pre_authorized()):
                            return Response({'error': 'Order has already been executed.'}, status=status.HTTP_400_BAD_REQUEST)

                        # gateway_process_payment(payment=payment, payment_token=payment_token)
                        gateway_authorize(payment=payment, payment_token=payment.token)

                        payment_info = create_payment_information(payment)
                        client_token = payment_gateway.get_client_token(connection_params=connection_params)

                elif payment_token_id:
                    customer_payment_token = get_object_or_404(customer.payment_token, id=payment_token_id)
                    payment_gateway, connection_params = get_payment_gateway(gateway_name=gateway)
                    extra_data = {'customer_user_agent': request.META.get('HTTP_USER_AGENT')}
                    with transaction.atomic():
                        payment = create_payment(
                            gateway=gateway,
                            currency=settings.DEFAULT_CURRENCY,
                            email=order.user_email,
                            billing_address=order.billing_address,
                            customer_ip_address=get_client_ip(request),
                            total=order.total,
                            order=order,
                            extra_data=extra_data)

                        if (order.is_fully_paid()
                                or payment.charge_status == ChargeStatus.FULLY_REFUNDED or order.is_pre_authorized()):
                            return Response({'error': 'Order has already been executed.'}, status=status.HTTP_400_BAD_REQUEST)

                        gateway_authorize(payment=payment, payment_token=customer_payment_token.token)

                        payment_info = create_payment_information(payment)
                        client_token = payment_gateway.get_client_token(connection_params=connection_params)

                # Change the status in the task after route calculations
                order.status = OrderStatus.CONFIRMED
                order.save()
                order.events.create(type=OrderEvents.PAYMENT_AUTHORIZED.value)

                # Calculate the route and driver payout
                signals.calculate_driver_payout.send(sender=None, customer=customer, order=order)

                # Notify vendor
                signals.order_placed.send(sender=None, customer=order.customer, order=order)
                # Post to slack
                signals.order_placed_slack.send(sender=None, customer=order.customer,
                                                order=order, vendor=order.vendor)

                # Notify vendor
                #signals.order_placed.send(sender=None, customer=customer, order=order)
                # Post to slack
                #signals.order_placed_slack.send(sender=None, customer=customer, order=order, vendor=order.vendor)

                order_serializer = OrderSerializer(order)
                return Response(order_serializer.data)
            else:
                return Response({'error': 'Please provide a correct order id'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            capture_exception(e)
            return Response({'error': 'Unknown error. Please contact our support.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)


# @permission_classes([IsAuthenticatedCustomer, ])
# class OrderPaymentView(APIView):
#     def post(self, request, format=None):
#         customer = get_object_or_404(Customer.objects.prefetch_related('payment_token'), user=request.user)

#         try:
#             json_data = json.loads(request.body)

#             order_id = json_data.get('order_id', -1)
#             #order = get_object_or_404(Order.objects.select_related('charge'), id=order_id)
#             order = Order.objects.get(id=order_id)

#             if order.is_pre_authorized():
#                 return Response({'error': 'Order #{} has been executed already.'.format(order.id)})
#             # if order.charge != None and order.charge == ChargeStatus.SUCCEDED:
#             #     return Response({"error": "Already paid for the order."},
#             #                     status=status.HTTP_400_BAD_REQUEST)

#             if 'payment_token_id' in json_data:
#                 customer_payment_token = customer.payment_token.get(id=json_data['payment_token_id'])
#                 if customer_payment_token:
#                     payment_token = PaymentToken.objects.get(id=customer_payment_token.id)
#                     # payment, _ = Payment.objects.get_or_create(
#                     #     gateway=PAYMENT_CHOICES[0[0]],
#                     #     is_active=True,
#                     #     order=order,
#                     #     customer_id=customer_payment_token.customer_id,
#                     #     customer_ip_address=get_client_ip(request),
#                     #     total=order.total,
#                     #     currency='GBP')
#                     if order.address:
#                         payment, _ = Payment.objects.get_or_create(
#                             gateway=PAYMENT_CHOICES[0][0],
#                             is_active=True,
#                             order=order,
#                             customer_id=customer_payment_token.customer_id,
#                             customer_ip_address=get_client_ip(request),
#                             total=order.total,
#                             billing_first_name=customer.user.first_name,
#                             billing_last_name=customer.user.last_name,
#                             billing_address_1=order.address.line1,
#                             billing_address_2=order.address.line2,
#                             billing_city=order.address.city,
#                             billing_city_area=order.address.city,
#                             billing_postal_code=order.address.postcode,
#                             billing_email=order.get_user_current_email(),
#                             currency=settings.DEFAULT_CURRENCY)
#                     else:
#                         payment, _ = Payment.objects.get_or_create(
#                             gateway=PAYMENT_CHOICES[0][0],
#                             is_active=True,
#                             order=order,
#                             customer_id=customer_payment_token.customer_id,
#                             customer_ip_address=get_client_ip(request),
#                             total=order.total,
#                             billing_first_name=customer.user.first_name,
#                             billing_last_name=customer.user.last_name,
#                             billing_email=order.get_user_current_email(),
#                             currency=settings.DEFAULT_CURRENCY)

#                     if (order.is_fully_paid() or payment.charge_status == ChargeStatus.FULLY_REFUNDED or order.is_pre_authorized()):
#                         return Response({"error": "Already paid for the order."}, status=status.HTTP_400_BAD_REQUEST)

#                     #payment_gateway, gateway_params = get_payment_gateway(payment.gateway)
#                     payment.authorize(payment_token=payment_token)

#                     # stripe.api_key = STRIPE_API_KEY

#                     # stripe_charge = stripe.Charge.create(
#                     #     amount=int(order.total * 100),
#                     #     currency='gbp',
#                     #     description='ORDER #{}'.format(order.id),
#                     #     customer=payment_token.customer_id,
#                     #     metadata={'order_id': order.id},
#                     #     capture=False,
#                     # )

#                     # charge = Charge.objects.create(
#                     #     order = order,
#                     #     charge_id=stripe_charge.id,
#                     #     customer_id=payment_token.customer_id,
#                     #     provider=payment_token.provider
#                     # )
#                     # order.charge = charge
#                 else:
#                     return Response({"error": "Payment token not found for customer"},
#                                     status=status.HTTP_400_BAD_REQUEST)
#             elif 'payment_token' in json_data:
#                 gateway = json_data.get('provider')
#                 extra_data = {'customer_user_agent': request.META.get('HTTP_USER_AGENT')}
#                 if gateway == 'stripe':
#                     #payment_gateway, connection_params = get_payment_gateway(gateway)
#                     payment_token = json_data.get('payment_token')

#                     with transaction.atomic():
#                         payment = create_payment(
#                         gateway=gateway,
#                         currency='GBP',
#                         email=order.user_email,
#                         billing_address=order.address,
#                         customer_ip_address=get_client_ip(request),
#                         total=order.total.gross.amount,
#                         order=order,
#                         extra_data=extra_data)

#                         payment_info = create_payment_information(payment)

#                     # if order.address:
#                     #     payment, _ = Payment.objects.get_or_create(
#                     #         gateway=PAYMENT_CHOICES[0][0],
#                     #         is_active=True,
#                     #         order=order,
#                     #         token=payment_token,
#                     #         customer_ip_address=get_client_ip(request),
#                     #         total=order.total,
#                     #         billing_first_name=customer.user.first_name,
#                     #         billing_last_name=customer.user.last_name,
#                     #         billing_address_1=order.address.line1,
#                     #         billing_address_2=order.address.line2,
#                     #         billing_city=order.address.city,
#                     #         billing_city_area=order.address.city,
#                     #         billing_postal_code=order.address.postcode,
#                     #         billing_email=order.get_user_current_email(),
#                     #         currency=settings.DEFAULT_CURRENCY)
#                     else:
#                         payment, _ = Payment.objects.get_or_create(
#                             gateway=PAYMENT_CHOICES[0][0],
#                             is_active=True,
#                             order=order,
#                             token=payment_token,
#                             customer_ip_address=get_client_ip(request),
#                             total=order.total,
#                             billing_first_name=customer.user.first_name,
#                             billing_last_name=customer.user.last_name,
#                             billing_email=order.get_user_current_email(),
#                             currency=settings.DEFAULT_CURRENCY)

#                     if (order.is_fully_paid() or payment.charge_status == ChargeStatus.FULLY_REFUNDED or order.is_pre_authorized()):
#                         return Response({"error": "Already paid for the order."}, status=status.HTTP_400_BAD_REQUEST)

#                     #payment_gateway, gateway_params = get_payment_gateway(payment.gateway)
#                     payment.authorize(payment_token=payment_token)

#                     # charge = Charge.objects.create(
#                     #     charge_id=stripe_charge.id,
#                     #     payment_token=stripe_token['id'],
#                     #     provider=provider
#                     # )
#                     # order.charge = charge
#                 else:
#                     return Response({"error": "Provider not supported"}, status=status.HTTP_400_BAD_REQUEST)
#             else:
#                 return Response({"error": "Payment ID or token needed"}, status=status.HTTP_400_BAD_REQUEST)

#         except PaymentError as e:
#             capture_exception(e)
#             exc_info = sys.exc_info()
#             newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
#             return Response({'error': 'There was an issue with the payment. {}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)
#         # except stripe.error.CardError as e:
#         #     exc_info = sys.exc_info()
#         #     newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
#         #     return Response({'error': 'There was an issue with the provided payment details.'}, status=status.HTTP_400_BAD_REQUEST)
#         # except stripe.error.StripeError as e:
#         #     exc_info = sys.exc_info()
#         #     newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
#         #     return Response({'error': 'There was an issue with the provided payment details.'}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             capture_exception(e)
#             exc_info = sys.exc_info()
#             # exc_type, exc_value, exc_traceback = sys.exc_info()
#             # print("*** print_tb:")
#             # traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
#             # print("*** print_exception:")
#             # traceback.print_exception(exc_type, exc_value, exc_traceback,
#             #                         limit=20, file=sys.stdout)
#             newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
#             return Response({'error': 'Internal error 1117. Please contact our support at support@halalivery.co.uk.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)

#         # return Response({'error': 'Internal error 1117. Please contact our support at support@halalivery.co.uk.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)
#         transfer = Transfer.objects.create(charge=payment)
#         order.transfer = transfer

#         # Change the status in the task after route calculations
#         order.status = OrderStatus.CONFIRMED
#         order.save()

#         # Calculate the route and driver payout
#         signals.calculate_driver_payout.send(sender=None, customer=customer, order=order)

#         # Notify vendor
#         signals.order_placed.send(sender=None, customer=order.customer, order=order)
#         # Post to slack
#         signals.order_placed_slack.send(sender=None, customer=order.customer,
#                                         order=order, vendor=order.vendor)

#         # Notify vendor
#         #signals.order_placed.send(sender=None, customer=customer, order=order)
#         # Post to slack
#         #signals.order_placed_slack.send(sender=None, customer=customer, order=order, vendor=order.vendor)

#         order_serializer = OrderSerializer(order)
#         return Response(order_serializer.data)


@permission_classes([IsAuthenticatedCustomer, ])
class OrderView(APIView):
    def get(self, request, order_id=None):
        customer = get_object_or_404(Customer, user=request.user)
        try:
            if order_id is None or order_id is '':
                orders = Order.objects.filter(customer=customer).order_by('-id')
                serializer = OrderSerializer(orders, many=True)
            else:
                orders = Order.objects.filter(customer=customer).get(id=order_id)
                serializer = OrderSerializer(orders)
        except Exception as ex:
            capture_exception(e)
            return Response({"error": "No such orders found for customer"},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data)
