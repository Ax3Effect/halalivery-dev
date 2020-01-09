from rest_framework import serializers

from decimal import Decimal
from django.utils import timezone
import datetime
from time import gmtime, strftime

from halalivery.delivery import DeliveryType
from halalivery.marketplaces.models import Restaurant, Grocery, PrepTime, ServiceableArea
from halalivery.order.models import Order, OrderItem
from halalivery.menu.models import Menu, MenuItem, MenuItemOption, MenuOptionsGroup, MenuCategory
from halalivery.menu.serializers import MenuSerializer, MenuLightSerializer, MenuItemSerializer, MenuItemOptionSerializer

from halalivery.basket.models import Basket, BasketItem
from halalivery.users.models import Address
from halalivery.users.serializers import VendorSerializer, CustomerAddressSerializer
from halalivery.coupons.utils import get_discount_amount

class PrepTimeSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()

    class Meta:
        model = PrepTime
        fields = ('busy_status', 'time')

    def get_time(self, obj):
        return obj.time()


class RestaurantSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    menu = MenuSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)

    class Meta:
        model = Restaurant
        depth = 2
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('menu__items')
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset

class RestaurantSingleSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    menu = MenuLightSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)

    class Meta:
        model = Restaurant
        depth = 2
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('marketplace__menu__categories')
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset

class RestaurantLightSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)

    class Meta:
        model = Restaurant
        depth = 2
        fields = ['vendor', 'prep_time', 'category', 'online', 'surcharge_amount', 'surcharge_threshold', 'operating_times']

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset


class GrocerySerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    menu = MenuSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)

    class Meta:
        model = Grocery
        depth = 2
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('menu__items')
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset

class ServiceableAreasSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceableArea
        depth = 2
        fields = ('city',)

class GrocerySingleSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    menu = MenuSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)
    areas = ServiceableAreasSerializer(many=True, read_only=True)

    class Meta:
        model = Grocery
        depth = 2
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('menu__categories')
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset

class GroceryLightSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    prep_time = PrepTimeSerializer(many=False, read_only=True)

    class Meta:
        model = Grocery
        depth = 2
        fields = ['vendor', 'prep_time', 'online', 'category', 'surcharge_amount', 'surcharge_threshold', 'operating_times']

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related('vendor')
        queryset = queryset.select_related('prep_time')

        return queryset

class OneSignalSerializer(serializers.ModelSerializer):
    onesignal = serializers.UUIDField()
