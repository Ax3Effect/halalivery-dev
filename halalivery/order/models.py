from django.db import models
from decimal import Decimal
from operator import attrgetter
from django.contrib.postgres.fields import JSONField
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from django.db.models import F, Max, Sum
from django.utils.timezone import now
from django.utils.translation import pgettext_lazy
from ..core.utils.json_serializer import CustomJsonEncoder
from django_measurement.models import MeasurementField
from django_prices.models import MoneyField, TaxedMoneyField
from ..core.utils.taxes import ZERO_TAXED_MONEY, zero_money
from ..core.weight import WeightUnits, zero_weight

from measurement.measures import Weight
from django.core.validators import MinValueValidator
from prices import Money


from halalivery.order import OrderStatus, OrderEvents, display_order_event
from halalivery.delivery import DeliveryType, DeliveryProvider
# Menu models
from halalivery.menu.models import MenuItem, MenuItemOption
# Account models
from halalivery.users.models import Customer, Vendor, Driver, Address
# Payment models
from halalivery.payment import ChargeStatus, TransactionKind

# Discounts
from halalivery.coupons.models import Coupon
from halalivery.partner_discounts.models import PartnerDiscount


# Create your models here.

class OrderQueryset(models.QuerySet):
    def confirmed(self):
        """Return non-draft orders."""
        return self.exclude(status=OrderStatus.DRAFT)

    def drafts(self):
        """Return draft orders."""
        return self.filter(status=OrderStatus.DRAFT)

    def internal_delivery(self):
        """Return orders delivered by internal drivers"""
        return self.filter(delivery_by=DeliveryProvider.CELERY, delivery_type=DeliveryType.DELIVERY)

    def ready_to_fulfill(self):
        """Return orders that can be fulfilled.

        Orders ready to fulfill are fully paid but unfulfilled (or partially
        fulfilled).
        """
        statuses = {OrderStatus.CONFIRMED, }
        qs = self.filter(status__in=statuses, payments__is_active=True)
        qs = qs.annotate(amount_paid=Sum('payments__captured_amount'))
        return qs.filter(total_gross__lte=F('amount_paid'))

    def ready_to_capture(self):
        """Return orders with payments to capture.

        Orders ready to capture are those which are not draft or canceled and
        have a preauthorized payment. The preauthorized payment can not
        already be partially or fully captured.
        """
        qs = self.filter(
            payments__is_active=True,
            payments__charge_status=ChargeStatus.NOT_CHARGED)
        qs = qs.exclude(status={OrderStatus.DRAFT, OrderStatus.CANCELED})
        return qs.distinct()

# class OrderItem(models.Model):
#     order = models.ForeignKey('Order', on_delete=models.CASCADE)
#     item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
#     quantity = models.PositiveSmallIntegerField(default=1)
#     mods = models.ManyToManyField(MenuItemOption, blank=True)

    # def __str__(self):
    #     return "Order #{} {}".format(self.order.id, self.item.name)

class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    time_placed = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=OrderStatus.CHOICES, default=OrderStatus.DRAFT)

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, related_name='orders')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL,
                               blank=True, null=True, related_name='orders',)
    language_code = models.CharField(
        max_length=35, default=settings.LANGUAGE_CODE)
    user_email = models.EmailField(blank=True, default='')
    # items = models.ManyToManyField(MenuItem, through=OrderItem, related_name='items')
    token = models.CharField(max_length=36, unique=True, blank=True)

    prep_time = models.FloatField(max_length=6)
    delivery_address = models.ForeignKey(
        Address, related_name='+', editable=False, null=True,
        on_delete=models.SET_NULL)
    billing_address = models.ForeignKey(
        Address, related_name='+', editable=False, null=True,
        on_delete=models.SET_NULL)
    delivery_type = models.CharField(
        max_length=32, choices=DeliveryType.CHOICES, default=DeliveryType.DELIVERY)
    delivery_by = models.CharField(max_length=32, choices=DeliveryProvider.CHOICES,
                                   default=DeliveryProvider.CELERY)
    confirmation_code = models.CharField(max_length=5)
    delivery_fee = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
                              decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    driver_tip = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
                            decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    surcharge = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
                           decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    subtotal = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
                          decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    total = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0.00))

    voucher = models.ForeignKey(
        Coupon, blank=True, null=True, related_name='+',
        on_delete=models.SET_NULL)
    discount_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0.00))
    partner_discount = models.ForeignKey(PartnerDiscount, blank=True, null=True, on_delete=models.SET_NULL)
    partner_discount_is_applied = models.BooleanField(default=False)
    customer_note = models.TextField(blank=True, null=True, default='')
    weight = MeasurementField(
        measurement=Weight, unit_choices=WeightUnits.CHOICES,
        default=zero_weight)

    objects = OrderQueryset.as_manager()

    class Meta:
        ordering = ('-pk', )
        permissions = ((
            'manage_orders',
            pgettext_lazy('Permission description', 'Manage orders.')),)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid4())
        return super().save(*args, **kwargs)

    def is_fully_paid(self):
        total_paid = self._total_paid()
        return total_paid >= self.total

    def is_partly_paid(self):
        total_paid = self._total_paid()
        return total_paid > 0

    def get_user_current_email(self):
        return self.customer.user.email if self.customer else self.user_email

    def _total_paid(self):
        # Get total paid amount from partially charged,
        # fully charged and partially refunded payments
        payments = self.payments.filter(
            charge_status__in=[
                ChargeStatus.PARTIALLY_CHARGED,
                ChargeStatus.FULLY_CHARGED,
                ChargeStatus.PARTIALLY_REFUNDED])
        total_captured = [
            payment.get_captured_amount() for payment in payments]
        total_paid = sum(total_captured)
        return total_paid

    def _index_billing_phone(self):
        return self.billing_address.phone

    def _index_shipping_phone(self):
        return self.shipping_address.phone

    def __iter__(self):
        return iter(self.lines.all())

    def __repr__(self):
        return '<Order #%r>' % (self.id,)

    def __str__(self):
        return '#%d' % (self.id,)

    def get_absolute_url(self):
        return reverse('order:details', kwargs={'token': self.token})

    def get_last_payment(self):
        return max(self.payments.all(), default=None, key=attrgetter('pk'))

    def get_payment_status(self):
        last_payment = self.get_last_payment()
        if last_payment:
            return last_payment.charge_status
        return ChargeStatus.NOT_CHARGED

    def get_payment_status_display(self):
        last_payment = self.get_last_payment()
        if last_payment:
            return last_payment.get_charge_status_display()
        return dict(ChargeStatus.CHOICES).get(ChargeStatus.NOT_CHARGED)

    def is_pre_authorized(self):
        return self.payments.filter(
            is_active=True,
            transactions__kind=TransactionKind.AUTH).filter(
                transactions__is_success=True).exists()

    @property
    def quantity_fulfilled(self):
        return sum([line.quantity_fulfilled for line in self])

    def is_shipping_required(self):
        return any(line.is_shipping_required for line in self)

    def get_subtotal(self):
        subtotal_iterator = (line.get_total() for line in self)
        return sum(subtotal_iterator)

    def get_total_quantity(self):
        return sum([line.quantity for line in self])

    def is_draft(self):
        return self.status == OrderStatus.DRAFT

    def is_open(self):
        statuses = {OrderStatus.CONFIRMED, }
        return self.status in statuses

    def can_cancel(self):
        return self.status not in {OrderStatus.CANCELED, OrderStatus.DRAFT}

    def can_capture(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        order_status_ok = self.status not in {
            OrderStatus.DRAFT, OrderStatus.CANCELED}
        return payment.can_capture() and order_status_ok

    def can_charge(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        order_status_ok = self.status not in {
            OrderStatus.DRAFT, OrderStatus.CANCELED}
        return payment.can_charge() and order_status_ok

    def can_void(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        return payment.can_void()

    def can_refund(self, payment=None):
        if not payment:
            payment = self.get_last_payment()
        if not payment:
            return False
        return payment.can_refund()

    def can_mark_as_paid(self):
        return len(self.payments.all()) == 0

    @property
    def total_authorized(self):
        payment = self.get_last_payment()
        if payment:
            return payment.get_authorized_amount()
        return zero_money()

    @property
    def total_captured(self):
        payment = self.get_last_payment()
        if payment and payment.charge_status in (
                ChargeStatus.PARTIALLY_CHARGED,
                ChargeStatus.FULLY_CHARGED,
                ChargeStatus.PARTIALLY_REFUNDED):
            return Money(payment.captured_amount, payment.currency)
        return zero_money()

    @property
    def total_balance(self):
        return self.total_captured - self.total

    def get_total_weight(self):
        return self.weight


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', editable=False, on_delete=models.CASCADE)
    # max_length is as produced by ProductVariant's display_product method
    item = models.ForeignKey(
        MenuItem, related_name='order_items',
        on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=386, null=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0.00))

    class Meta:
        ordering = ('pk', )

    def __str__(self):
        return self.name

    def get_total(self):
        total = Decimal(0.00)
        total += self.price * self.quantity
        for i in self.mods.all():
            total += i.price * self.quantity
        return total

    @property
    def quantity_unfulfilled(self):
        return self.quantity - self.quantity_fulfilled


class OrderItemMod(models.Model):
    order_line = models.ForeignKey(OrderItem, related_name='mods', editable=False, on_delete=models.CASCADE)
    name = models.CharField(max_length=386, null=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal(0.00))

    class Meta:
        ordering = ('pk', )

    def __str__(self):
        return self.name

    def get_total(self):
        return self.price * self.quantity


class OrderEvent(models.Model):
    """Model used to store events that happened during the order lifecycle.

        Args:
            parameters: Values needed to display the event on the storefront
            type: Type of an order
    """
    date = models.DateTimeField(default=now, editable=False)
    type = models.CharField(
        max_length=255,
        choices=((event.name, event.value) for event in OrderEvents))
    order = models.ForeignKey(
        Order, related_name='events', on_delete=models.CASCADE)
    parameters = JSONField(
        blank=True, default=dict, encoder=CustomJsonEncoder)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True,
        on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ('date', )

    def __repr__(self):
        return 'OrderEvent(type=%r, user=%r)' % (self.type, self.user)

    def get_event_display(self):
        return display_order_event(self)
