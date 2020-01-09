from rest_framework import serializers

from halalivery.marketplaces.serializers import PrepTimeSerializer
from halalivery.menu.serializers import MenuItemSerializer, MenuItemOptionSerializer
from halalivery.basket.models import Basket, BasketItem, BasketItemMod
from halalivery.users.serializers import CustomerAddressSerializer
from halalivery.coupons.utils import get_discount_amount
from halalivery.coupons import DiscountType

class BasketItemModSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = BasketItemMod
        depth = 2
        fields = ('name', 'quantity', 'price')

    def get_price(self, obj):
        return obj.get_price()
    
    def get_name(self, obj):
        return obj.mod.name

class BasketItemSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer()
    mods = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = BasketItem
        depth = 2
        fields = ('item', 'mods', 'quantity', 'total')

    def get_mods(self, obj):
        qset = obj.mods.all()
        return [BasketItemModSerializer(m).data for m in qset]

    def get_total(self, obj):
        return obj.get_total()

class BasketSerializer(serializers.ModelSerializer):
    vendor_id = serializers.IntegerField(source="vendor.id")
    prep_time = serializers.SerializerMethodField() # PrepTimeSerializer(many=False, read_only=True, source="vendor.marketplace.prep_time")
    items = serializers.SerializerMethodField()
    delivery_fee = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    surcharge = serializers.SerializerMethodField()
    surcharge_threshold = serializers.IntegerField(source="vendor.marketplace.surcharge_threshold")
    discount_amount = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    voucher_type = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    driver_tip = serializers.SerializerMethodField()
    address = CustomerAddressSerializer(many=False, read_only=True)

    class Meta:
        model = Basket
        depth = 2
        fields = (
            'vendor_id',
            'prep_time',
            'address',
            'items',
            'note',
            'delivery_type',
            'driver_tip',
            'delivery_fee',
            'driver_tip',
            'surcharge',
            'surcharge_threshold',
            'discount_amount',
            'discount_type',
            'voucher_code',
            'voucher_type',
            'subtotal',
            'total')
        # extra_kwargs = {'vendor_type': {'write_only': True}}

    def get_driver_tip(self, obj):
        return obj.driver_tip

    def get_delivery_fee(self, obj):
        delivery_fee = obj.get_delivery_fee()
        return delivery_fee

    def get_subtotal(self, obj):
        # subtotal = obj.get_subtotal()
        # subtotal -= obj.get_discount_amount()
        
        # # if subtotal < Decimal('0.0'):
        # #     subtotal = Decimal('0.0')

        # subtotal = round(subtotal, 2)
        subtotal = obj.get_subtotal()
        return subtotal

    def get_discount_amount(self, obj):
        discount_amount = obj.get_discount_amount()
        return discount_amount

    def get_discount_type(self, obj):
        if obj.partner_discount:
            return DiscountType.PARTNER
        elif obj.voucher:
            return DiscountType.VOUCHER
        else:
            return None
        
    def get_total(self, obj):
        return obj.get_total()

    def get_surcharge(self, obj):
        return obj.get_surcharge()

    # def items_qset(self, obj):
    #     qset = BasketItem.objects.filter(basket=obj)
    #     return qset

    def get_prep_time(self, obj):
        if obj.vendor and obj.vendor.marketplace().prep_time:
            return obj.vendor.marketplace().prep_time.time()

    def get_items(self, obj):
        qset = BasketItem.objects.filter(basket=obj).only('item')
        return [BasketItemSerializer(m).data for m in qset]

    def get_voucher_discount(self, obj):
        if obj.voucher:
            return obj.voucher.value
        else:
            return None

    def get_voucher_code(self, obj):
        if obj.voucher:
            return obj.voucher.code
        else:
            return None

    def get_voucher_type(self, obj):
        if obj.voucher:
            return obj.voucher.type
        else:
            return None

