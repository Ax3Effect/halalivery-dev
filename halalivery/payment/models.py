from django.db import models

from decimal import Decimal
from operator import attrgetter
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator

from . import (ChargeStatus, CustomPaymentChoices, TransactionError, TransactionKind, TransferError, TransferParty)
from halalivery.order.models import Order
from halalivery.basket.models import Basket

from ..core.utils.taxes import zero_money
from prices import Money

class Payment(models.Model):
    """A model that represents a single payment.

    This might be a transactable payment information such as credit card
    details, gift card information or a customer's authorization to charge
    their PayPal account.

    All payment process related pieces of information are stored
    at the gateway level, we are operating on the reusable token
    which is a unique identifier of the customer for given gateway.

    Several payment methods can be used within a single order. Each payment
    method may consist of multiple transactions.
    """

    gateway = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    charge_status = models.CharField(
        max_length=20, choices=ChargeStatus.CHOICES,
        default=ChargeStatus.NOT_CHARGED)
    token = models.CharField(max_length=128, blank=True, default='')
    total = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal('0.0'))
    captured_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal('0.0'))
    transfered_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal('0.0'))
    currency = models.CharField(max_length=10)  # FIXME: add ISO4217 validator

    checkout = models.ForeignKey(
        Basket, null=True, related_name='payments', on_delete=models.SET_NULL)
    order = models.ForeignKey(
        Order, null=True, related_name='payments', on_delete=models.PROTECT)

    billing_email = models.EmailField(blank=True)
    billing_first_name = models.CharField(max_length=256, blank=True)
    billing_last_name = models.CharField(max_length=256, blank=True)
    billing_company_name = models.CharField(max_length=256, blank=True)
    billing_address_1 = models.CharField(max_length=256, blank=True)
    billing_address_2 = models.CharField(max_length=256, blank=True)
    billing_city = models.CharField(max_length=256, blank=True)
    billing_city_area = models.CharField(max_length=128, blank=True)
    billing_postal_code = models.CharField(max_length=256, blank=True)
    billing_country_code = models.CharField(max_length=2, blank=True)
    billing_country_area = models.CharField(max_length=256, blank=True)

    cc_first_digits = models.CharField(max_length=6, blank=True, default='')
    cc_last_digits = models.CharField(max_length=4, blank=True, default='')
    cc_brand = models.CharField(max_length=40, blank=True, default='')
    cc_exp_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        null=True, blank=True)
    cc_exp_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1000)], null=True, blank=True)

    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
    extra_data = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('pk', )

    def __repr__(self):
        return 'Payment(gateway=%s, is_active=%s, created=%s, charge_status=%s)' % (
            self.gateway, self.is_active, self.created, self.charge_status)

    def get_last_transaction(self):
        return max(self.transactions.all(), default=None, key=attrgetter('pk'))

    def get_total(self):
        return Money(self.total, self.currency or settings.DEFAULT_CURRENCY)

    def get_authorized_amount(self):
        money = Decimal(0.00)

        # Query all the transactions which should be prefetched
        # to optimize db queries
        transactions = self.transactions.all()

        # There is no authorized amount anymore when capture is succeeded
        # since capture can only be made once, even it is a partial capture
        if any([txn.kind == TransactionKind.CAPTURE
                and txn.is_success for txn in transactions]):
            return money

        # Filter the succeeded auth transactions
        authorized_txns = [
            txn for txn in transactions
            if txn.kind == TransactionKind.AUTH and txn.is_success]

        # Calculate authorized amount from all succeeded auth transactions
        for txn in authorized_txns:
            money += txn.amount

        # If multiple partial capture is supported later though it's unlikely,
        # the authorized amount should exclude the already captured amount here
        return money

    def get_captured_amount(self):
        return self.captured_amount

    def get_charge_amount(self):
        """Retrieve the maximum capture possible."""
        return self.total - self.captured_amount

    @property
    def is_authorized(self):
        return any([
            txn.kind == TransactionKind.AUTH
            and txn.is_success for txn in self.transactions.all()])

    @property
    def not_charged(self):
        return self.charge_status == ChargeStatus.NOT_CHARGED

    def can_authorize(self):
        return self.is_active and self.not_charged

    def can_capture(self):
        return self.is_active and self.not_charged and self.is_authorized

    def can_charge(self):
        not_fully_charged = (
            self.charge_status == ChargeStatus.PARTIALLY_CHARGED)
        return self.is_active and (self.not_charged or not_fully_charged)

    def can_void(self):
        return self.is_active and self.not_charged and self.is_authorized

    def can_refund(self):
        can_refund_charge_status = (
            ChargeStatus.PARTIALLY_CHARGED,
            ChargeStatus.FULLY_CHARGED,
            ChargeStatus.PARTIALLY_REFUNDED)
        return (
            self.is_active and self.charge_status in can_refund_charge_status
            and self.gateway != CustomPaymentChoices.MANUAL)
    
    def can_transfer(self, amount=0):
        return amount + self.transfered_amount <= self.captured_amount


class Transaction(models.Model):
    """Represents a single payment operation.
    Transaction is an attempt to transfer money between your store
    and your customers, with a chosen payment method.
    """

    created = models.DateTimeField(auto_now_add=True, editable=False)
    payment = models.ForeignKey(
        Payment, related_name='transactions', on_delete=models.PROTECT)
    token = models.CharField(max_length=128, blank=True, default='')
    kind = models.CharField(max_length=10, choices=TransactionKind.CHOICES)
    is_success = models.BooleanField(default=False)
    currency = models.CharField(max_length=10)
    amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.0'))
    error = models.CharField(
        choices=[(tag, tag.value) for tag in TransactionError],
        max_length=256, null=True)
    gateway_response = JSONField(encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ('pk', )

    def __repr__(self):
        return 'Transaction(type=%s, is_success=%s, created=%s)' % (
            self.kind, self.is_success, self.created)
    
    def __str__(self):
        return 'Transaction(type=%s, is_success=%s, created=%s, payment=%s)' % (
            self.kind, self.is_success, self.created, self.payment.id)

    def get_amount(self):
        return Money(self.amount, self.currency or settings.DEFAULT_CURRENCY)

class Transfer(models.Model):
    """Represents a single payment operation.

    Transaction is an attempt to transfer money between your store
    and your customers, with a chosen payment method.
    """

    created = models.DateTimeField(auto_now_add=True, editable=False)
    charge = models.ForeignKey(Payment, related_name='transfers', on_delete=models.PROTECT)
    transfer_id = models.CharField(max_length=50, blank=True, null=True)
    destination = models.CharField(max_length=50, blank=True, null=True)
    is_success = models.BooleanField(default=False)
    transfer_party = models.CharField(max_length=10, choices=TransferParty.CHOICES, default=TransferParty.VENDOR)
    currency = models.CharField(max_length=10, default=settings.DEFAULT_CURRENCY)
    # Unified error code across all payment gateways
    error = models.CharField(
        choices=[(tag, tag.value) for tag in TransferError],
        max_length=256, null=True)
    amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.0'))
    description = models.CharField(max_length=50, blank=True, null=True)
    source_type = models.CharField(max_length=50, blank=True, null=True)
    source_transaction = models.CharField(max_length=50, blank=True, null=True)
    transfer_group = models.CharField(max_length=50, blank=True, null=True)
    gateway_response = JSONField(encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ('pk', )

    def __repr__(self):
        return 'Transaction(type=%s, is_success=%s, created=%s)' % (
            self.kind, self.is_success, self.created)

    def __str__(self):
        return 'Transfer #{} Transfer party {}'.format(self.id, self.transfer_party)
    
    def get_amount(self):
        return Money(self.amount, self.currency or settings.DEFAULT_CURRENCY)
