from rest_framework import serializers

from halalivery.order.models import Order, OrderItem
from halalivery.marketplaces.models import PrepTime, OperatingTime, Restaurant, Grocery
from halalivery.menu.models import Menu
from halalivery.delivery import DeliveryProvider, DeliveryType
from halalivery.order.serializers import OrderItemSerializer
from halalivery.menu.serializers import MenuItemSerializer, MenuOptionsGroupSerializer, VendorMenuCategorySerializer
from halalivery.users.serializers import AddressSerializer, CustomerAddressSerializer, VendorSerializer

from decimal import Decimal
from halalivery.helpers import vendor_order_total, HALALIVERY_PERCENT, HALALIVERY_ADDITIONAL_FEE


class VendorOrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    halalivery_fee_amount = serializers.SerializerMethodField()
    driver_tip = serializers.SerializerMethodField()
    surcharge = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'items', 'delivery_address', 'status', 'prep_time', 'delivery_type', 'driver', 'driver_phone', 'customer', 'customer_phone', 'created_at', 'time_placed', 'customer_note', 'halalivery_fee_amount', 'surcharge', 'driver_tip', 'subtotal', 'total')

    def get_items(self, obj):
        qset = OrderItem.objects.filter(order=obj).only('item')
        return [OrderItemSerializer(m).data for m in qset]

    def get_delivery_address(self, obj):
        if obj.delivery_type == DeliveryProvider.VENDOR:
            delivery_address = AddressSerializer(obj.delivery_address).data
            line1 = delivery_address['street_address_1']
            line2 = delivery_address['street_address_2']
            postcode = delivery_address['postcode']
            city = delivery_address['city']
            return "{}, {}, {}, {}".format(line1, line2, postcode, city)
        else:
           return None
    
    def get_customer(self, obj):
        #if obj.delivery_type == DeliveryType.SELF_PICKUP or obj.delivery_type == DeliveryType.VENDOR:
            return "{} {}.".format(obj.customer.user.first_name, obj.customer.user.last_name[:1]).title()
        #else:
        #    return None

    def get_customer_phone(self,obj):
        #if obj.delivery_type == DeliveryType.SELF_PICKUP or obj.delivery_type == DeliveryType.VENDOR:
        if obj.delivery_address:
            return "{}".format(obj.delivery_address.phone or obj.delivery_address)
        #else:
        #    return None

    def get_driver(self, obj):
        if obj.delivery_type == DeliveryProvider.CELERY:
            if obj.driver:
                return "{} {}.".format(obj.driver.user.first_name, obj.driver.user.last_name[:1]).title()
            else:
                return None
    
    def get_driver_phone(self, obj):
        if obj.delivery_type == DeliveryProvider.CELERY:
            if obj.driver:
                return "{}".format(obj.driver.address.phone)
            else:
                return None

    def get_halalivery_fee_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        fee = Decimal('0.00')
        
        # If delivery give surcharge to the owner
        if obj.delivery_by == DeliveryProvider.VENDOR:
            subtotal += self.get_surcharge(obj)
        
        subtotal += self.get_driver_tip(obj)
        
        fee += subtotal * HALALIVERY_PERCENT

        # If Halalivery delivery charge vendor 1.5
        if obj.delivery_by == DeliveryProvider.CELERY:
            # subtotal -= HALALIVERY_ADDITIONAL_FEE
            fee += HALALIVERY_ADDITIONAL_FEE

        return fee

    def get_subtotal(self, obj):
        vendor_total = obj.subtotal + obj.discount_amount
        #return vendor_order_total(order=obj.order)
        return Decimal(vendor_total)
    
    def get_surcharge(self, obj):
        if obj.delivery_type == DeliveryProvider.VENDOR:
            return obj.surcharge
        else:
            return Decimal('0.00')
    
    def get_driver_tip(self, obj):
        if obj.delivery_type == DeliveryProvider.VENDOR:
            return obj.driver_tip
        else:
            return Decimal('0.00')

    def get_total(self, obj):
        # vendor_total = self.get_subtotal(obj)
        # vendor_total -= self.get_halalivery_fee_amount(obj)
        # vendor_total += self.get_driver_tip(obj)
        # vendor_total += self.get_surcharge(obj)
        vendor_total = vendor_order_total(order=obj)
        return Decimal(vendor_total)
        #return vendor_order_total(order=obj.order)
        #return vendor_total

class PrepTimeVendorSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()

    class Meta:
        model = PrepTime
        fields = ('busy_status', 'time', 'quiet_time', 'moderate_time', 'busy_time')

    def get_time(self, obj):
        return obj.time()

class VendorOperatingTimeSerializer(serializers.ModelSerializer):
    weekday = serializers.SerializerMethodField()

    class Meta:
        model = OperatingTime
        fields = ('weekday', 'from_hour', 'to_hour')

    def get_weekday(self, obj):
        return obj.get_weekday_display()

class MenuVendorSerializer(serializers.HyperlinkedModelSerializer):
    items_options_groups = MenuOptionsGroupSerializer(many=True, read_only=True)
    categories = VendorMenuCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        depth = 2
        fields = ('categories', 'items_options_groups')

class VendorRestaurantProfileSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    prep_time = PrepTimeVendorSerializer(many=False, read_only=True)

    class Meta:
        model = Restaurant
        depth = 2
        fields = '__all__'

class VendorGroceryProfileSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)
    prep_time = PrepTimeVendorSerializer(many=False, read_only=True)

    class Meta:
        model = Grocery
        depth = 2
        fields = '__all__'

