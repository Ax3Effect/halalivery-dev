import datetime
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from halalivery.menu.serializers import MenuItemSerializer, MenuItemOptionSerializer
from halalivery.order.models import OrderItem, Order, OrderItemMod
from halalivery.users.serializers import VendorSerializer, CustomerAddressSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    mods = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('name', 'quantity', 'mods', 'total')
    
    def get_mods(self, obj):
        qset = obj.mods.all()
        return [MenuItemOptionSerializer(m).data for m in qset]

    def get_total(self, obj):
        return obj.get_total()

class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    vendor = VendorSerializer(many=False, read_only=True)
    address = CustomerAddressSerializer(many=False, read_only=True)
    delivery_time = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    voucher = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        extra_kwargs = {'confirmation_code': {'write_only': True}, 'charge': {'write_only': True}, 'transfer': { 'write_only': True }}

    def get_items(self, obj):
        qset = obj.items.all() #OrderItem.objects.filter(order=obj)
        return [OrderItemSerializer(m).data for m in qset]

    def get_delivery_time(self, obj):
        time_placed = obj.time_placed
        time_placed = timezone.localtime(time_placed)
        if not time_placed:
            time_placed = obj.updated_at
        now = timezone.localtime(timezone.now())
        prep_time = obj.prep_time
        if obj.delivery_type == 2:
            ptime = time_placed + datetime.timedelta(minutes=prep_time)
        else:
            ptime = time_placed + datetime.timedelta(minutes=prep_time) + datetime.timedelta(minutes=20)

        tm = ptime
        discard = datetime.timedelta(minutes=tm.minute % 5,
                                     seconds=tm.second,
                                     microseconds=tm.microsecond)
        tm -= discard
        if discard >= datetime.timedelta(minutes=5):
            tm += datetime.timedelta(minutes=10)

        start_interval = tm - datetime.timedelta(minutes=5)
        end_interval = tm + datetime.timedelta(minutes=5)

        interval = "{}-{}".format(start_interval.strftime("%H:%M"), end_interval.strftime("%H:%M"))

        return interval

    def get_voucher(self, obj):
        if obj.voucher:
            return obj.voucher.code
        else:
            return None

    def get_weight(self, obj):
        return obj.get_total_weight().value
