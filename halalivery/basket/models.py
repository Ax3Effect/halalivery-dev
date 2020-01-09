from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator

from django.conf import settings
from ..core.utils.taxes import zero_money, ZERO_TAXED_MONEY
from django_measurement.models import MeasurementField
from django_prices.models import MoneyField, TaxedMoneyField
from prices import Money


from halalivery.menu.models import MenuItem, MenuItemOption
from halalivery.users.models import Customer, Driver, Vendor, Address
from halalivery.delivery import DeliveryType, DeliveryProvider
from halalivery.coupons.models import Coupon
from halalivery.coupons.utils import get_discount_amount
from halalivery.coupons import DiscountType
from halalivery.partner_discounts.models import PartnerDiscount

from halalivery.delivery.utils import get_delivery_fee

# Create your models here.
class BasketItemMod(models.Model):
    basket_item = models.ForeignKey('BasketItem', blank=True, null=True,
                             related_name='mods', on_delete=models.CASCADE)
    mod = models.ForeignKey(MenuItemOption, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return "{} - {}".format(self.mod, self.quantity)

    def get_price(self):
        return self.mod.price

class BasketItem(models.Model):
    basket = models.ForeignKey('Basket', blank=True, null=True, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, related_name='+', on_delete=models.CASCADE)
    # mods = models.ManyToManyField(MenuItemOption, through=BasketItemMod)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def get_total(self):
        """Return the total price of this line."""
        amount = Decimal(0.00)
        amount += self.quantity * self.item.get_price()
        mods = (mod.get_price() * mod.quantity for mod in self.mods.all())
        # * self.quantity
        # for mod in self.mods.all():
        #     amount += mod.get_price() * self.quantity
        amount += sum(mods)
        
        return amount

class Basket(models.Model):
    """Customer's basket."""
    customer = models.ForeignKey(Customer, blank=True, null=True,
                                 related_name='baskets', on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True)
    delivery_type = models.CharField(
        max_length=32, choices=DeliveryType.CHOICES, default=DeliveryType.DELIVERY)
    driver_tip = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    note = models.TextField(blank=True, default='')

    voucher = models.ForeignKey(Coupon, on_delete=models.PROTECT, blank=True, null=True)
    partner_discount = models.ForeignKey(PartnerDiscount, blank=True, null=True, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        ordering = ('-updated_at', )

    def __str__(self):
        return "{} basket".format(self.customer)

    def __iter__(self):
        return iter(self.items.all())

    def __len__(self):
        return self.items.count()

    def return_items(self):
        return self.items.all()

    def return_basket(self):
        basket_items = BasketItem.objects.filter(basket=self).all()
        return basket_items

    def get_subtotal(self):
        subtotals = (item.get_total() for item in self)
        return sum(subtotals)

    def get_surcharge(self):
        surcharge = Decimal(0.00)
        subtotal = self.get_subtotal()
        surcharge_threshold = self.vendor.marketplace().surcharge_threshold
        if subtotal < surcharge_threshold:
            surcharge = surcharge_threshold - subtotal
        return surcharge

    def get_delivery_fee(self):
        total = self.get_subtotal() + self.get_surcharge() - self.get_discount_amount()
        if self.delivery_type != DeliveryType.SELF_PICKUP:
            total += Decimal(self.driver_tip)
        delivery_fee = get_delivery_fee(order=self, total=total)
        return delivery_fee

    def get_discount_amount(self):
        if self.partner_discount:
            if self.partner_discount.is_valid():
                discount_amount = self.get_subtotal() * (self.partner_discount.amount / 100)
                return discount_amount
        discount_amount = get_discount_amount(voucher=self.voucher, amount=self.get_subtotal())
        return discount_amount

    def get_total(self):
        """Return the total cost of the cart."""
        total = self.get_subtotal() + self.get_delivery_fee() + self.get_surcharge() - self.get_discount_amount()
        if self.delivery_type != DeliveryType.SELF_PICKUP:
            total += Decimal(self.driver_tip)
        return total

    # def return_basket(self):
    #     basket_items = BasketItem.objects.filter(basket=self).all()
    #     return basket_items

    # def get_subtotal(self):
    #     items = self.return_basket()
    #     subtotal = Decimal('0.00')
    #     for i in items:
    #         subtotal += i.item.price * i.quantity
    #         for y in i.mods.all():
    #             subtotal += y.price * i.quantity
    #     return subtotal
