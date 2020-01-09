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
import sys
import traceback
import newrelic.agent
from sentry_sdk import capture_exception

from halalivery.vendors import VendorType
from halalivery.marketplaces.models import Restaurant, Grocery, MarketplaceVisibillity
from halalivery.basket.models import Basket, BasketItemMod, BasketItem
from halalivery.basket.serializers import BasketSerializer
from halalivery.order.models import Order, OrderItem
from halalivery.order import OrderStatus
from halalivery.menu.models import MenuItem, MenuItemOption, Menu, MenuCategory
from halalivery.delivery import DeliveryType
from .serializers import GroceryLightSerializer, GrocerySingleSerializer
from halalivery.users.models import Customer, Address, PaymentToken, Vendor
from halalivery.users.permissions import IsAuthenticatedCustomer

from . import signals

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

# Postgis
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance

from halalivery.drivers.gateways.stuart import StuartClient

PAYMENT_CHOICES = [
    (k, v) for k, v in settings.CHECKOUT_PAYMENT_GATEWAYS.items()]


@permission_classes([AllowAny, ])
class MarketplaceView(APIView):
    def get(self, request, vendor_id=None):
        vendor_id = request.GET.get("vendor_id", None)
        if vendor_id is not None:
            vendor = get_object_or_404(Vendor, id=vendor_id)
            marketplace = vendor.marketplace()
            if marketplace != None:
                if marketplace.is_available():
                    if vendor.vendor_type == VendorType.GROCERY:
                        return Response(GrocerySingleSerializer(marketplace).data)
                else:
                    return Response({'error': '{} is currently offline. Please come back later.'.format(vendor.vendor_name)}, status=status.HTTP_406_NOT_ACCEPTABLE)
        return Response({'error': 'Not allowed'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            response = json.loads(request.body)
            latitude = response.get('latitude')
            longitude = response.get('longitude')

            if not latitude or not longitude or not isinstance(latitude, float) or not isinstance(longitude, float):
                return Response({'error': 'Please use a correct location data.'}, status=status.HTTP_400_BAD_REQUEST)

            users_location = Point((longitude, latitude))

            radius = MarketplaceVisibillity.objects.filter().last()
            radius = radius.distance

            # Optimised code
            now = timezone.localtime(timezone.now())
            weekday = now.isoweekday()
            now_time = now.time()

            # start and end is on the same day
            q1 = Q(weekday=weekday, from_hour__lte=now_time, to_hour__gte=now_time)

            # start and end are not on the same day and we test on the start day
            q2 = Q(weekday=weekday, from_hour__lte=now_time, to_hour__lt=F('from_hour'))

            # If monday
            if weekday == 1:
                q3 = Q(weekday=7, from_hour__gte=now_time, to_hour__gte=now_time, to_hour__lt=F('from_hour'))
            else:
                q3 = Q()

            # start and end are not on the same day and we test on the end day
            q4 = Q(weekday=(weekday-1), from_hour__gte=now_time,
                   to_hour__gte=now_time, to_hour__lt=F('from_hour'))

            oper_times = OperatingTime.objects.filter(q1 | q2 | q3 | q4)

            available_groceries = Grocery.objects.filter(online=True, areas__area__contains=users_location, vendor__address__point__distance_lte=(users_location, Distance(mi=radius)), operating_times__in=oper_times)\
                .select_related('vendor', 'prep_time').prefetch_related('areas', 'category', 'operating_times')
            sorted_groceries = sorted(available_groceries, key=lambda a: a.prep_time.time())
            grocery_serializer = GroceryLightSerializer(sorted_groceries, many=True)

            if not grocery_serializer.data:
                return Response({"error": "Everything is closed at this moment."},
                                status=status.HTTP_404_NOT_FOUND)

            return Response(grocery_serializer.data)
        except Exception as e:
            return Response({"error": "Internal error: 100. Unknown error. {}".format(e)},
                            status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticatedCustomer, ])
class BasketView(APIView):

    def get(self, request, format=None):
        basket = get_object_or_404(Basket, customer__user=request.user)
        serializer = BasketSerializer(basket)
        return Response(serializer.data)

    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        basket, created = Basket.objects.get_or_create(customer=customer)
        basket.items.clear()

        try:
            json_data = json.loads(request.body)
            vendor_id = json_data.get('vendor_id', None)
            basket_data = json_data.get('basket', None)
            self_pickup = json_data.get('self_pickup', None)
            driver_tip = json_data.get('driver_tip', Decimal('0.00'))
            customer_note = json_data.get('customer_note', '')
            voucher_code = json_data.get('voucher_code', None)
            address_id = json_data.get('address_id', None)

            vendor = get_object_or_404(Vendor, pk=vendor_id)

            if not vendor.marketplace().is_available():
                return Response({"error": "{} is not available.".format(vendor)}, status=status.HTTP_404_NOT_FOUND)

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

                basket_item, _ = BasketItem.objects.get_or_create(
                    basket=basket, item=menu_item, quantity=quantity)
                mods = item.get("mods", None)

                if mods:
                    for mod in mods:
                        menu_item_mod = MenuItemOption.objects.get(pk=mod)
                        basket_item_mod = BasketItemMod.objects.get_or_create(
                            item=basket_item, mod=menu_item_mod)

            basket.vendor = vendor
            basket.self_pickup = self_pickup
            basket.driver_tip = driver_tip
            basket.note = customer_note
            # now = timezone.localtime(timezone.now())

            partner_discount = PartnerDiscount.objects.filter(vendor=vendor).first()
            if partner_discount:
                # if partner_discount.is_valid() and voucher_code:
                #     return Response({'error': 'Unable to use voucher with partnership discount'},
                #                     status=status.HTTP_400_BAD_REQUEST)
                if partner_discount.is_valid():
                    basket.partner_discount = partner_discount
                else:
                    basket.partner_discount = None
            else:
                basket.partner_discount = None

            if voucher_code is not None and not partner_discount:
                # Coupon.objects.active(date=now)
                voucher = Coupon.objects.filter(code__iexact=voucher_code).first()

                #voucher = get_voucher_for_cart(voucher_code, voucher)
                if voucher_code and not voucher:
                    basket.voucher = None
                    # return Response({'error': 'Voucher code is not applicable'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    customer_has_orders = Order.objects.filter(customer=customer).exists()
                    if customer_has_orders and not voucher.expired() and not voucher.is_redeemed and not voucher.redeemed_by_user(customer):
                        basket.voucher = voucher
                    else:
                        basket.voucher = None
            else:
                basket.voucher = None

            if address_id and isinstance(address_id, int) and not self_pickup:
                customer_address = customer.address.filter(id=address_id)
                if customer_address.exists():
                    # Validate address with stuart
                    response = StuartClient().validate_address(customer_address.first(), delivery_type='delivering')
                    vendor_response = StuartClient().validate_address(vendor.address, delivery_type='picking')
                    if not response or not vendor_response:
                        return Response({"error": "Cannot deliver from {} to {}. Only a self pickup is available.".format(vendor.address.postcode, customer_address.first().postcode)})
                    basket.address = customer_address.first()
                else:
                    return Response({"error": "Provided address does not belong to the current customer."},
                                    status=status.HTTP_400_BAD_REQUEST)
            elif address_id is None or self_pickup:
                basket.address = None

            else:
                return Response({"error": "Please provide a delivery address"})

            basket.save()

        except Exception as e:
            capture_exception(e)
            return Response({"error": "Internal error: 100. Unknown error.{}".format(e)},
                            status=status.HTTP_400_BAD_REQUEST)

@permission_classes(IsAdminUser,)
def stripeTestPage(request):
    order = get_object_or_404(Order, pk=request.GET.get('order_id'))
    order_info = ""
    for i in order.return_items():
        print(i)
        # return HttpResponse({"breakpoint"})
        order_info += "<p>* {} (£{}) q: {} items, ".format(i.item.name, i.item.price, i.quantity)
        for y in i.mods.all():
            order_info += "Mod: {} (£{}) ".format(y.name, y.price)

        order_info += "</p>"

    context = {
        "user": request.user,
        "order_info": order_info,
        "order_amount": order.total,
        "order_id": order.id,
        "amount": int(
            order.total*100),
        "stripe_pb_key": 'pk_test_fLKIE8jofqmvVt2sGlK1VcG7'}
    return render(request, 'stripeTestPage.html', context)


# @permission_classes(IsAdminUser)
# @api_view(['GET'])
# def transport_to_custom_categories(request):
#     """
#     Creates MenuCategories for every Menu separately (it allows to customise sorting).
#     If there are already MenuCategories they are going to be deleted and new are going to be created
#     """
#     menus = Menu.objects.all().prefetch_related('items')
#     menu_item_categories = MenuItemCategory.objects.all()
#     menu_categories = MenuCategory.objects.all()
#     menu_categories.delete()

#     for menu in menus:
#         for menu_item_category in menu_item_categories:
#             menu_items_per_category = menu.items.filter(category=menu_item_category)
#             if menu_items_per_category:
#                 menu_category = MenuCategory(name=menu_item_category.name, menu=menu)
#                 menu_category.save()
#                 for menu_item in menu_items_per_category:
#                     menu_item.menu_category = menu_category
#                     menu_item.save()
#     return Response({'transported': 'ok'})

@permission_classes(IsAdminUser)
@api_view(['POST'])
def increase_prices(request):
    json_data = json.loads(request.body)
    vendor_id = json_data.get('vendor_id', None)
    increase_amount = json_data.get('increase_amount', Decimal('0.00'))
    category_name = json_data.get('category_name', None)

    #menu_items_per_category = menu.items.filter(category=menu_item_category)
    if vendor_id:
        vendor = get_object_or_404(Vendor, id=vendor_id)
        menu = vendor.marketplace().menu
        menu_category = get_object_or_404(MenuCategory, name=category_name, menu=menu)
        menu_items_per_category = menu.items.filter(menu_category=menu_category)
        for item in menu_items_per_category:
            item.price += Decimal(increase_amount)
            item.save()
    return Response({'ok': 'Successfully increased prices for {} by {}'.format(vendor, increase_amount)})

@permission_classes(IsAdminUser)
@api_view(['POST'])
def create_address_points(request):

    addresses = Address.objects.all()

    #menu_items_per_category = menu.items.filter(category=menu_item_category)
    for address in addresses:
        address.save()
    return Response({'ok': 'Successfully saved points for {} addresses'.format(addresses.count())})

    # menu = Menu.objects.filter(id=5).prefetch_related('items').first()
    # menu_item_categories = MenuItemCategory.objects.all()
    # for menu_item_category in menu_item_categories:
    #     if menu_item_category.name == 'Beans':
    #         #print(menu_item_category)
    #         menu_items_per_category = menu.items.filter(category=menu_item_category)
    #         beans = menu_items_per_category #.filter(category=138)
    #         for bean in beans:
    #             print('OLD {} PRICE: {}'.format(bean.name, bean.price))
    #             bean.price += Decimal('0.12')
    #             bean.save()
    #             print('NEW {} PRICE: {}'.format(bean.name, bean.price))
    #             #bean.save()
    #         print(beans)

    # OLD BASKET
    #  json_data = json.loads(request.body)
    #         vendor_id = json_data["vendor_id"]
    #         basket_data = json_data["basket"]
    #         self_pickup = json_data["self_pickup"]
    #         driver_tip = json_data["driver_tip"]
    #         customer_note = json_data.get("customer_note", '')
    #         voucher_code = json_data.get('voucher_code', None)

    #         vendor = get_object_or_404(Vendor, id=vendor_id)

    #         if not vendor.marketplace().is_available():
    #             return Response({"error": "Vendor is no longer available."}, status=status.HTTP_404_NOT_FOUND)

    #         marketplace = vendor.marketplace()
    #         categories = marketplace.menu.categories.all()
    #         q1 = Q(menu_category__in=categories)
    #         q2 = Q(related_menu=marketplace.menu)
    #         q3 = Q(available=True)
    #         menu_items = MenuItem.objects.filter(q1 | q2 | q3)
    #         for i in basket_data["items"]:
    #             menu_item = MenuItem.objects.get(id=i["item_id"])

    #             if menu_item not in menu_items:
    #                 return Response({"error": "{} is not on the menu.".format(menu_item.name)}, status=status.HTTP_404_NOT_FOUND)
    #             if not menu_item.available:
    #                 return Response({"error": "{} is not available.".format(menu_item.name)})

    #             item = BasketItem.objects.create(basket=basket, item=menu_item, quantity=i['q'])

    #             if i.get("mods", None):
    #                 for y in i.get("mods"):
    #                     mod = MenuItemOption.objects.get(id=y)
    #                     item.mods.add(mod)

    #             item.save()

    #         basket.vendor = marketplace.vendor
    #         basket.self_pickup = self_pickup
    #         basket.driver_tip = driver_tip
    #         basket.note = customer_note
    #         # now = timezone.localtime(timezone.now())

    #         partner_discount = PartnerDiscount.objects.filter(vendor=vendor).first()
    #         if partner_discount:
    #             # if partner_discount.is_valid() and voucher_code:
    #             #     return Response({'error': 'Unable to use voucher with partnership discount'},
    #             #                     status=status.HTTP_400_BAD_REQUEST)
    #             if partner_discount.is_valid():
    #                 basket.partner_discount = partner_discount

    #         if voucher_code is not None and not partner_discount:
    #             voucher = Coupon.objects.filter(code__iexact=voucher_code).first()  # Coupon.objects.active(date=now)

    #             #voucher = get_voucher_for_cart(voucher_code, voucher)
    #             if voucher_code and not voucher:
    #                 basket.voucher = None
    #                 # return Response({'error': 'Voucher code is not applicable'}, status=status.HTTP_404_NOT_FOUND)
    #             else:
    #                 customer_has_orders = Order.objects.filter(customer=customer).exists()
    #                 if customer_has_orders and not voucher.expired() and not voucher.is_redeemed and not voucher.redeemed_by_user(customer):
    #                     basket.voucher = voucher
    #                 else:
    #                     basket.voucher = None
    #         else:
    #             basket.voucher = None

    #         basket.save()

    # if request.data.get("postcode", None) is None or request.data.get("postcode", "") is "":
    #         return Response({"error": "Please enter a postcode"}, status=status.HTTP_400_BAD_REQUEST)
    #     r = requests.get("https://api.postcodes.io/postcodes/{}".format(request.data.get("postcode")))
    #     r_json = r.json()
    #     if r_json["status"] == 404:
    #         return Response({"error": "The postcode you entered was not correct"},
    #                         status=status.HTTP_400_BAD_REQUEST)
    #     outcode = r_json["result"]["outcode"]

    #     # Optimised code
    #     now = timezone.localtime(timezone.now())
    #     weekday = now.isoweekday()
    #     now_time = now.time()

    #     # start and end is on the same day
    #     q1 = Q(weekday=weekday, from_hour__lte=now_time, to_hour__gte=now_time)

    #     # start and end are not on the same day and we test on the start day
    #     q2 = Q(weekday=weekday, from_hour__lte=now_time, to_hour__lt=F('from_hour'))

    #     # If monday
    #     if weekday == 1:
    #         q3 = Q(weekday=7, from_hour__gte=now_time, to_hour__gte=now_time, to_hour__lt=F('from_hour'))
    #     else:
    #         q3 = Q()

    #     # start and end are not on the same day and we test on the end day
    #     q4 = Q(weekday=(weekday-1), from_hour__gte=now_time,
    #            to_hour__gte=now_time, to_hour__lt=F('from_hour'))

    #     oper_times = OperatingTime.objects.filter(q1 | q2 | q3 | q4)

    #     restaurant_serializer = None
    #     grocery_serializer = None

    # if request.data.get("include_menu", None) is None or request.data.get("include_menu", "") is "" or request.data.get("include_menu", None) == True:
    #     available_restaurants = Restaurant.objects.filter(areas__outcode=outcode, online=True, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time', 'menu').prefetch_related('areas', 'category', 'operating_times', 'menu__categories', 'menu__categories__items')
    #     sorted_restaurants = sorted(available_restaurants, key=lambda a: a.prep_time.time())
    #     restaurant_serializer = RestaurantSerializer(sorted_restaurants, many=True)
    # else:
    #     available_restaurants = Restaurant.objects.filter(areas__outcode=outcode, online=True, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time').prefetch_related('areas', 'category', 'operating_times')
    #     sorted_restaurants = sorted(available_restaurants, key=lambda a: a.prep_time.time())
    #     restaurant_serializer = RestaurantLightSerializer(sorted_restaurants, many=True)

    # if request.data.get("include_menu", None) is None or request.data.get("include_menu", "") is "" or request.data.get("include_menu", None) == True:
    #     available_groceries = Grocery.objects.filter(online=True, areas__outcode=outcode, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time', 'menu').prefetch_related('areas', 'category', 'operating_times', 'menu__categories', 'menu__categories__items')
    #     sorted_groceries = sorted(available_groceries, key=lambda a: a.prep_time.time())
    #     grocery_serializer = GrocerySerializer(sorted_groceries, many=True)
    # else:
    #     available_groceries = Grocery.objects.filter(online=True, areas__outcode=outcode, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time').prefetch_related('areas', 'category', 'operating_times')
    #     sorted_groceries = sorted(available_groceries, key=lambda a: a.prep_time.time())
    #     grocery_serializer = GroceryLightSerializer(sorted_groceries, many=True)
    # available_restaurants = Restaurant.objects.filter(areas__outcode=outcode, online=True, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time').prefetch_related('areas', 'category', 'operating_times')
    # sorted_restaurants = sorted(available_restaurants, key=lambda a: a.prep_time.time())
    # restaurant_serializer = RestaurantLightSerializer(sorted_restaurants, many=True)

    # available_groceries = Grocery.objects.filter(online=True, areas__outcode=outcode, operating_times__in=oper_times)\
    #         .select_related('vendor', 'prep_time').prefetch_related('areas', 'category', 'operating_times')
    # sorted_groceries = sorted(available_groceries, key=lambda a: a.prep_time.time())
    # grocery_serializer = GroceryLightSerializer(sorted_groceries, many=True)
    # # if not restaurant_serializer.data and not grocery_serializer.data:
    # #     return Response({"error": "No open restaurants or groceries found"},
    # #                     status=status.HTTP_404_NOT_FOUND)
    # # response_dic = {"restaurants": restaurant_serializer.data,
    # #                 "groceries": grocery_serializer.data}
    # return Response(grocery_serializer.data)
