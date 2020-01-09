# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import requests
import datetime as dt
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

# Time libs
from django.utils import timezone
from decimal import Decimal

# Error catching
import sys, traceback
import newrelic.agent
from sentry_sdk import capture_exception


from halalivery.marketplaces.models import Restaurant, Grocery, MarketplaceVisibillity
from halalivery.basket.models import Basket, BasketItemMod, BasketItem
from halalivery.order.models import Order, OrderItem
from halalivery.order import OrderStatus
from halalivery.menu.models import MenuItem, MenuItemOption, Menu, MenuCategory
from halalivery.delivery import DeliveryType
from .serializers import BasketSerializer
from halalivery.users.models import Customer, Address, PaymentToken, Vendor
from halalivery.users.permissions import IsAuthenticatedCustomer

# Payments
from halalivery.payment import ChargeStatus, PaymentError
from halalivery.payment.models import Payment
from halalivery.payment.utils import get_payment_gateway
from halalivery.payment.models import Transfer

from halalivery.partner_discounts.models import PartnerDiscount

from halalivery.coupons.models import Coupon
from halalivery.coupons.utils import get_voucher_for_cart, increase_voucher_usage
from halalivery.helpers import get_client_ip
from halalivery.marketplaces.models import OperatingTime

#Postgis
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance 

from ..core.utils.taxes import zero_money

from halalivery.drivers.gateways.stuart import StuartClient


# Create your views here.

@permission_classes([IsAuthenticatedCustomer, ])
class BasketView(APIView):

    def get(self, request, format=None):
        basket = get_object_or_404(Basket, customer__user=request.user)
        serializer = BasketSerializer(basket)
        return Response(serializer.data)

    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        basket, _ = Basket.objects.get_or_create(customer=customer)
        basket.items.clear()

        try:
            json_data = json.loads(request.body)
            vendor_id = json_data.pop('vendor_id', None)
            basket_data = json_data.pop('basket', None)
            delivery_type = json_data.pop('delivery_type', DeliveryType.DELIVERY)
            driver_tip = json_data.pop('driver_tip', zero_money)
            customer_note = json_data.pop('customer_note', '')
            voucher_code = json_data.pop('voucher_code', None)
            address_id = json_data.pop('address_id', None)

            vendor = get_object_or_404(Vendor, pk=vendor_id)

            basket.vendor = vendor
            basket.driver_tip = driver_tip
            basket.note = customer_note
            basket.delivery_type = delivery_type
            basket.subtotal = basket.get_subtotal()
            basket.total = basket.get_total()
            basket.save()

            if not vendor.marketplace().is_available():
                return Response({"error": "{} is not available.".format(vendor)}, status=status.HTTP_404_NOT_FOUND)

            if address_id and isinstance(address_id, int) and delivery_type != DeliveryType.SELF_PICKUP:
                customer_address = get_object_or_404(customer.address, id=address_id)
                users_location = Point((customer_address.longitude, customer_address.latitude))
                if not vendor.marketplace().areas.filter(area__contains=users_location):
                    basket.address = None
                    return Response({'error': 'Delivery to the selected address is not available. Only a self pickup option is available.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                # ServicableArea.objects.filter(users_location = Point((longitude, latitude)))
                #if vendor.address__point__distance_lte=(users_location, Distance(mi=radius))
                # distance = get_gmaps_distance(from_address=vendor.address, to_address=customer_address)
                # Validate address with stuart
                # response = StuartClient().validate_address(customer_address, delivery_type='delivering')
                # vendor_response = StuartClient().validate_address(vendor.address, delivery_type='picking')
                # if not response or not vendor_response:
                #     return Response({"error": "Cannot deliver from {} to {}. Only a self pickup is available.".format(vendor.address.postcode, customer_address.postcode)})
                basket.address = customer_address
            else:
                return Response({"error": "Provided address does not belong to the customer."},
                                    status=status.HTTP_400_BAD_REQUEST)
            
            if delivery_type == DeliveryType.SELF_PICKUP:
                basket.address = None
        
            
            marketplace = vendor.marketplace()
            categories = marketplace.menu.categories.all()
            q1 = Q(menu_category__in=categories)
            q2 = Q(related_menu=marketplace.menu)
            q3 = Q(available=True)
            menu_items = MenuItem.objects.filter(q1 | q2 | q3)
            
            for item in basket_data.get("items"):
                item_id = item.get("item_id", None)
                quantity = item.get('q', None)
                menu_item = get_object_or_404(MenuItem, pk=item_id)
                
                # If menu item is not part of the vendor's menu
                if menu_item not in menu_items:
                    return Response({"error": "{} is not on the menu.".format(menu_item.name)}, status=status.HTTP_404_NOT_FOUND)
                # If menu item is not availble on the vendor's menu
                if not menu_item.available:
                    return Response({"error": "{} is not available.".format(menu_item.name)})
                
                basket_item, _ = BasketItem.objects.get_or_create(basket=basket, item=menu_item, quantity=quantity)
                mods = item.get("mods", None)

                if mods:
                    for mod in mods:
                        menu_item_mod = MenuItemOption.objects.get(pk=mod)
                        basket_item_mod, _ = BasketItemMod.objects.get_or_create(basket_item=basket_item, mod=menu_item_mod, quantity=quantity)

            # now = timezone.localtime(timezone.now())

            partner_discount = PartnerDiscount.objects.filter(vendor=vendor).first()
            if partner_discount:
                if partner_discount.is_valid() and voucher_code:
                    return Response({'error': 'Unable to use voucher with a vendor discount'},
                                    status=status.HTTP_400_BAD_REQUEST)
                elif partner_discount.is_valid() and partner_discount.has_spent_minimum(amount=basket.get_subtotal()):
                    basket.partner_discount = partner_discount
                else:
                    basket.partner_discount = None
            else:
                basket.partner_discount = None

            if voucher_code is not None and not partner_discount:
                voucher = Coupon.objects.filter(code__iexact=voucher_code).first()  # Coupon.objects.active(date=now)
                
                if voucher_code and not voucher:
                    basket.voucher = None
                    return Response({'error': 'Voucher code is not applicable'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    customer_has_orders = Order.objects.filter(customer=customer).exists()
                    if customer_has_orders and not voucher.expired() and not voucher.is_redeemed and not voucher.redeemed_by_user(customer):
                        voucher.validate_min_amount_spent(basket.get_subtotal())
                        basket.voucher = voucher
                    else:
                        basket.voucher = None
            else:
                basket.voucher = None

            basket.save()

            serializer = BasketSerializer(basket)
            return Response(serializer.data)
            
        except Exception as e:
            capture_exception(e)
            exc_info = sys.exc_info()
            newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
            return Response({'error': '{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticatedCustomer, ])
class ValidateVoucher(APIView):
    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        try:
            json_data = json.loads(request.body)
            voucher_code = json_data.get('voucher_code', None)
            if voucher_code is not None:
                voucher = Coupon.objects.get(code__iexact=voucher_code)
                if voucher_code and not voucher:
                    return Response({'error': 'Voucher code is not applicable'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    customer_has_orders = Order.objects.filter(customer=customer).exists()
                    if customer_has_orders and not voucher.expired() and not voucher.is_redeemed and not voucher.redeemed_by_user(customer):
                        return Response({'success': 'Voucher code has been validated.'})
                    elif voucher.expired():
                        return Response({'error': 'Voucher code has expired.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif voucher.is_redeemed:
                        return Response({'error': 'Voucher code usage limit has exceed.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif voucher.redeemed_by_user(customer):
                        return Response({'error': 'You have used this voucher code before.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif not customer_has_orders:
                        return Response({'error': 'You will get a 10% discount on your first order anyway. Save the voucher for your next order :)'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        return Response({'error': 'Internal error 701. Please contact our support team at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)

        except Coupon.DoesNotExist:
            return Response({'error': 'Voucher code is invalid.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': 'Internal error 701. Please contact our support team at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'Internal error 702. Please contact our support team at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)
