from rest_framework import serializers
from halalivery.users.models import Driver
from halalivery.users.serializers import UserSerializer, AddressSerializer, DestinationSerializer
from halalivery.order.models import Order, OrderItem
from halalivery.order.serializers import OrderItemSerializer
from halalivery.vendors.serializers import VendorSerializer
from halalivery.drivers.models import DriverLocation
from halalivery.order import OrderStatus

class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    address = AddressSerializer(many=False, read_only=True)
    last_location = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = ('id', 'user', 'online', 'last_location', 'address', 'transport_type', 'avatar')

    def get_last_location(self, obj):
        try:
            location = obj.get_last_location()
            return DriverLocationSerializer(location).data
        except Exception:
            pass
            '''
            raise serializers.ValidationError(
                {'error': 'Error parsing the request. Make sure all the required fields are present.'}
            )
            '''


class DriverSummaryOrderSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(many=False, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'vendor', 'driver_tip', 'status', 'created_at', 'updated_at')


class DriverSummarySerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    address = AddressSerializer(many=False, read_only=True)
    orders = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = ('id', 'user', 'online', 'orders', 'address', 'transport_type', 'avatar')

    def get_orders(self, obj):
        from_date = self.context.get('from_date')
        to_date = self.context.get('to_date')

        if from_date is not None and to_date is not None:
            qset = Order.objects.filter(driver=obj).filter(created_at__range=[from_date, to_date], status__range=(6,8))
        else:
            qset = Order.objects.filter(driver=obj, status__range=(6,8))
        return [DriverSummaryOrderSerializer(m).data for m in qset]


class DriverActiveOrderSerializer(serializers.ModelSerializer):
    pickup = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'pickup', 'delivery', 'driver_tip', 'prep_time', 'status', 'updated_at', 'time_placed', 'items')

    def get_pickup(self, obj):
        return DestinationSerializer(obj.vendor.address, context={'vendor': obj.vendor}).data
    
    def get_delivery(self, obj):
        return DestinationSerializer(obj.delivery_address, context={'customer': obj.customer}).data

    def get_items(self, obj):
        if obj.status in (OrderStatus.READY_FOR_PICKUP, OrderStatus.DRIVER_ARRIVED, OrderStatus.DRIVER_COLLECTED):
            qset = obj.items.all()
            return [OrderItemSerializer(m).data for m in qset]
        else:
            return None

class DriverLiveOrderSerializer(serializers.ModelSerializer):
    destination = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'prep_time', 'status', 'updated_at', 'time_placed', 'destination')

    def get_destination(self, obj):
        return DestinationSerializer(obj.vendor.address, context={'vendor': obj.vendor}).data

class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverLocation
        fields = ('latitude','longitude')
