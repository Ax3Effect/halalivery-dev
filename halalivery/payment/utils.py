import json
import logging
from decimal import Decimal
from functools import wraps
from typing import Dict

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils.translation import pgettext_lazy

from ..users.models import Address, User
from ..basket.models import Basket
from ..core import analytics
from ..order import OrderEvents, OrderEventsEmails
#from ..order.emails import send_payment_confirmation
from ..order.models import Order
from . import (
    ChargeStatus, CustomPaymentChoices, GatewayError, OperationType,
    PaymentError, TransactionKind, get_payment_gateway)
from .models import Payment, Transaction, Transfer, TransferParty

logger = logging.getLogger(__name__)

GENERIC_TRANSACTION_ERROR = 'Transaction was unsuccessful'
REQUIRED_GATEWAY_KEYS = {
    'transaction_id', 'is_success', 'kind', 'error', 'amount', 'currency'}
ALLOWED_GATEWAY_KINDS = {choices[0] for choices in TransactionKind.CHOICES}

from sentry_sdk import capture_exception


def get_gateway_operation_func(gateway, operation_type):
    """Return gateway method based on the operation type to be performed."""
    if operation_type == OperationType.PROCESS_PAYMENT:
        return gateway.process_payment
    if operation_type == OperationType.TRANSFER:
        return gateway.transfer
    if operation_type == OperationType.AUTH:
        return gateway.authorize
    if operation_type == OperationType.CAPTURE:
        return gateway.capture
    if operation_type == OperationType.CHARGE:
        return gateway.charge
    if operation_type == OperationType.VOID:
        return gateway.void
    if operation_type == OperationType.REFUND:
        return gateway.refund


def create_payment_information(
        payment: Payment,
        payment_token: str = None,
        amount: Decimal = None,
        **extra_params
        ) -> Dict:
    """Extracts order information along with payment details.

    Returns information required to process payment and additional
    billing/shipping addresses for optional fraud-prevention mechanisms.
    """
    return {
        'token': payment_token,
        'amount': amount or payment.total,
        'currency': payment.currency,
        'billing': (
            payment.order.billing_address.as_data()
            if payment.order.billing_address else None),
        'delivery': (
            payment.order.delivery_address.as_data()
            if payment.order.delivery_address else None),
        'order_id': payment.order.id,
        'customer_ip_address': payment.customer_ip_address,
        'customer_email': payment.billing_email}


def create_transfer_information(
        payment: Payment,
        payment_token: str = None,
        amount: Decimal = None,
        destination: str = None,
        transfer_from_balance: bool = False,
        description: str = None,
        metadata: Dict = None,
        transfer_party: str = None,
        transfer_group: str = None) -> Dict:

    """Extracts order information along with payment details.

    Returns information required to process payment and additional
    billing/shipping addresses for optional fraud-prevention mechanisms.
    """
    return {
        'token': payment_token,
        'amount': amount or payment.total,
        'currency': payment.currency,
        'description': description,
        'metadata': metadata,
        'destination': destination,
        'transfer_from_balance': transfer_from_balance,
        'transfer_party': transfer_party,
        'transfer_group': transfer_group,
        'order_id': payment.order.id,
        'customer_ip_address': payment.customer_ip_address,
        'customer_email': payment.billing_email}


def handle_fully_paid_order(order):
    order.events.create(type=OrderEvents.ORDER_FULLY_PAID.value)
    if order.get_user_current_email():
        # send_payment_confirmation.delay(order.pk)
        order.events.create(
            type=OrderEvents.EMAIL_SENT.value,
            parameters={
                'email': order.get_user_current_email(),
                'email_type': OrderEventsEmails.PAYMENT.value})
    try:
        analytics.report_order(order.tracking_client_id, order)
    except Exception:
        # Analytics failing should not abort the checkout flow
        logger.exception('Recording order in analytics failed')


def require_active_payment(view):
    """Require an active payment instance.

    Decorate a view to check if payment is authorized, so any actions
    can be performed on it.
    """
    @wraps(view)
    def func(payment: Payment, *args, **kwargs):
        if not payment.is_active:
            raise PaymentError('This payment is no longer active.')
        return view(payment, *args, **kwargs)
    return func


def create_payment(
        gateway: str,
        total: Decimal,
        currency: str,
        email: str,
        billing_address: Address,
        customer_ip_address: str = '',
        payment_token: str = '',
        extra_data: Dict = None,
        checkout: Basket = None,
        order: Order = None) -> Payment:
    """Create a payment instance.

    This method is responsible for creating payment instances that works for
    both Django views and GraphQL mutations.
    """
    defaults = {}
    if billing_address:
        defaults = {
            'billing_email': email,
            'billing_first_name': billing_address.first_name,
            'billing_last_name': billing_address.last_name,
            'billing_company_name': billing_address.company_name,
            'billing_address_1': billing_address.street_address_1,
            'billing_address_2': billing_address.street_address_2,
            'billing_city': billing_address.city,
            'billing_postal_code': billing_address.postal_code,
            'billing_country_code': billing_address.country.code,
            'billing_country_area': billing_address.country_area,
            'currency': currency,
            'gateway': gateway,
            'total': total}
    else:
        defaults = {
            'billing_email': order.get_user_current_email(),
            'billing_first_name': order.customer.user.first_name,
            'billing_last_name': order.customer.user.last_name,
            'currency': currency,
            'gateway': gateway,
            'total': total
        }

    if extra_data is None:
        extra_data = {}

    data = {
        'is_active': True,
        'customer_ip_address': customer_ip_address,
        'extra_data': extra_data,
        'token': payment_token}

    if order is not None:
        data['order'] = order
    if checkout is not None:
        data['checkout'] = checkout

    payment, _ = Payment.objects.get_or_create(defaults=defaults, **data)
    return payment


@transaction.atomic
def mark_order_as_paid(order: Order, request_user: User):
    """Mark order as paid.

    Allows to create a payment for an order without actually performing any
    payment by the gateway.
    """
    payment = create_payment(
        gateway=CustomPaymentChoices.MANUAL,
        payment_token='',
        currency=order.total.gross.currency,
        email=order.user_email,
        billing_address=order.billing_address,
        total=order.total.gross.amount,
        order=order)
    payment.charge_status = ChargeStatus.FULLY_CHARGED
    payment.captured_amount = order.total.gross.amount
    payment.save(update_fields=['captured_amount', 'charge_status'])
    order.events.create(
        type=OrderEvents.ORDER_MARKED_AS_PAID.value, user=request_user)


def create_transaction(
        payment: Payment, kind: str, payment_information: Dict,
        gateway_response: Dict = None, error_msg=None) -> Transaction:
    """Create a transaction based on transaction kind and gateway response."""
    if gateway_response is None:
        gateway_response = {}

    # Default values for token, amount, currency are only used in cases where
    # response from gateway was invalid or an exception occured
    txn = Transaction.objects.create(
        payment=payment,
        kind=gateway_response.get('kind', kind),
        token=gateway_response.get(
            'transaction_id', payment_information['token']),
        is_success=gateway_response.get('is_success', False),
        amount=gateway_response.get('amount', payment_information['amount']),
        currency=gateway_response.get(
            'currency', payment_information['currency']),
        error=gateway_response.get('error', error_msg),
        gateway_response=gateway_response)
    return txn


def create_transfer(
        payment: Payment, transfer_information: Dict = None,
        gateway_response: Dict = None, error_msg=None) -> Transfer:
    """Create a transaction based on transaction kind and gateway response."""
    if gateway_response is None:
        gateway_response = {}

    # Default values for token, amount, currency are only used in cases where
    # response from gateway was invalid or an exception occured
    txn = Transfer.objects.create(
        charge=payment,
        description=gateway_response.get('description', 'ORDER #'),
        transfer_party=transfer_information['transfer_party'],
        transfer_group=gateway_response.get('transfer_group', 'ORDER #'),
        source_type=gateway_response.get(
            'source_type', transfer_information['token']),
        source_transaction=gateway_response.get(
            'source_transaction', transfer_information['token']),
        transfer_id=gateway_response.get(
            'id', transfer_information['token']),
        is_success=gateway_response.get('is_success', False),
        amount=gateway_response.get('amount', transfer_information['amount']),
        currency=gateway_response.get(
            'currency', transfer_information['currency']),
        error=gateway_response.get('error', error_msg),
        gateway_response=gateway_response)
    return txn


def gateway_get_client_token(gateway_name: str):
    """Gets client token, that will be used as a customer's identificator for
    client-side tokenization of the chosen payment method.
    """
    gateway, gateway_params = get_payment_gateway(gateway_name)
    return gateway.get_client_token(connection_params=gateway_params)


def clean_charge(payment: Payment, amount: Decimal):
    """Check if payment can be charged."""
    if amount <= 0:
        raise PaymentError('Amount should be a positive number.')
    if not payment.can_charge():
        raise PaymentError('This payment cannot be charged.')
    if amount > payment.total or amount > (
            payment.total - payment.captured_amount):
        raise PaymentError('Unable to charge more than un-captured amount.')


def clean_capture(payment: Payment, amount: Decimal):
    """Check if payment can be captured."""
    if amount <= 0:
        raise PaymentError('Amount should be a positive number.')
    if not payment.can_capture():
        raise PaymentError('This payment cannot be captured.')
    if amount > payment.total or amount > (
            payment.total - payment.captured_amount):
        raise PaymentError('Unable to capture more than authorized amount.')


def clean_authorize(payment: Payment):
    """Check if payment can be authorized."""
    if not payment.can_authorize():
        raise PaymentError('Charged transactions cannot be authorized again.')


def clean_mark_order_as_paid(order: Order):
    """Check if an order can be marked as paid."""
    if order.payments.exists():
        raise PaymentError(
            pgettext_lazy(
                'Mark order as paid validation error',
                'Orders with payments can not be manually marked as paid.'))


def call_gateway(operation_type, payment, payment_token, **extra_params):
    """Helper that calls the passed gateway function and handles exceptions.

    Additionally does validation of the returned gateway response.
    """
    gateway, connection_params = get_payment_gateway(payment.gateway)
    gateway_response = None
    error_msg = None

    payment_information = create_payment_information(
        payment, payment_token, **extra_params
    )

    transfer_information = create_transfer_information(
        payment, payment_token, **extra_params
    )

    try:
        func = get_gateway_operation_func(gateway, operation_type)
    except AttributeError:
        error_msg = 'Gateway doesn\'t implement {} operation'.format(
            operation_type.name)
        logger.exception(error_msg)
        raise PaymentError(error_msg)

    # The transaction kind is provided as a default value
    # for creating transactions when gateway has invalid response
    # The PROCESS_PAYMENT operation has CAPTURE as default transaction kind
    # For other operations, the transaction kind is same wtih operation type
    default_transaction_kind = TransactionKind.CAPTURE
    if operation_type != OperationType.PROCESS_PAYMENT:
        default_transaction_kind = getattr(
            TransactionKind, OperationType(operation_type).name)

    # Validate the default transaction kind
    if default_transaction_kind not in dict(TransactionKind.CHOICES):
        error_msg = 'The default transaction kind is invalid'
        logger.exception(error_msg)
        raise PaymentError(error_msg)

    try:
        gateway_response = None
        if operation_type != OperationType.TRANSFER:
            gateway_response = func(
                payment_information=payment_information,
                connection_params=connection_params)
        else:
            gateway_response = func(
                payment_information=transfer_information,
                connection_params=connection_params)
            validate_gateway_response(gateway_response)
    except GatewayError:
        error_msg = 'Gateway response validation failed'
        logger.exception(error_msg)
        gateway_response = None  # Set response empty as the validation failed
    except Exception as e:
        capture_exception(e)
        error_msg = 'Gateway encountered an error'
        logger.exception(error_msg)
    finally:
        if not isinstance(gateway_response, list):
            gateway_response = [gateway_response]
        transactions = []
        transfers = []
        for response in gateway_response:
            transactions.append(create_transaction(
                payment=payment,
                kind=default_transaction_kind,
                payment_information=payment_information,
                error_msg=error_msg,
                gateway_response=response))
        if operation_type == OperationType.TRANSFER:
            for response in gateway_response:
                transfers.append(create_transfer(
                payment=payment,
                transfer_information=transfer_information,
                error_msg=error_msg,
                gateway_response=response))

    for transaction in transactions:
        if not transaction.is_success:
            # Attempt to get errors from response, if none raise a generic one
            raise PaymentError(transaction.error or GENERIC_TRANSACTION_ERROR)

    return transactions[-1]


def validate_gateway_response(responses):
    """Validates response to be a correct format for Saleor to process."""
    if not isinstance(responses, (dict, list)):
        raise GatewayError('Gateway needs to return a dictionary or a list')

    if not isinstance(responses, list):
        responses = [responses]

    field_types = {
        'amount': Decimal,
        'currency': str,
        'is_success': bool,
        'kind': str,
        'transaction_id': str,
        'error': (type(None), str),
    }

    for response in responses:
        if not REQUIRED_GATEWAY_KEYS.issubset(response):
            raise GatewayError(
                'Gateway response needs to contain following keys: {}'.format(
                    sorted(REQUIRED_GATEWAY_KEYS)))

        for name, value in response.items():
            if name in field_types:
                if not isinstance(value, field_types[name]):
                    raise GatewayError('{} must be of type {}, was {}'.format(
                        name, field_types[name], type(value)))

        if response['kind'] not in ALLOWED_GATEWAY_KINDS:
            raise GatewayError(
                'Gateway response kind must be one of {}'.format(
                    sorted(ALLOWED_GATEWAY_KINDS)))

        if response['currency'] != settings.DEFAULT_CURRENCY:
            logger.warning('Transaction currency is different than Saleor\'s.')

        try:
            json.dumps(response, cls=DjangoJSONEncoder)
        except (TypeError, ValueError):
            raise GatewayError(
                'Gateway response needs to be json serializable')


def _gateway_postprocess(transaction, payment):
    transaction_kind = transaction.kind

    if transaction_kind in [TransactionKind.CHARGE, TransactionKind.CAPTURE]:
        payment.captured_amount += transaction.amount

        # Set payment charge status to fully charged
        # only if there is no more amount needs to charge
        payment.charge_status = ChargeStatus.PARTIALLY_CHARGED
        if payment.get_charge_amount() <= 0:
            payment.charge_status = ChargeStatus.FULLY_CHARGED

        payment.save(update_fields=['charge_status', 'captured_amount'])
        order = payment.order
        if order and order.is_fully_paid():
            handle_fully_paid_order(order)

    elif transaction_kind == TransactionKind.TRANSFER:
        payment.transfered_amount += transaction.amount
        payment.save(update_fields=['transfered_amount'])

    elif transaction_kind == TransactionKind.VOID:
        payment.is_active = False
        payment.save(update_fields=['is_active'])

    elif transaction_kind == TransactionKind.REFUND:
        changed_fields = ['captured_amount']
        payment.captured_amount -= transaction.amount
        payment.charge_status = ChargeStatus.PARTIALLY_REFUNDED
        if payment.captured_amount <= 0:
            payment.charge_status = ChargeStatus.FULLY_REFUNDED
            payment.is_active = False
        changed_fields += ['charge_status', 'is_active']
        payment.save(update_fields=changed_fields)


@require_active_payment
def gateway_process_payment(
        payment: Payment, payment_token: str) -> Transaction:
    """Performs whole payment process on a gateway."""
    transaction = call_gateway(
        operation_type=OperationType.PROCESS_PAYMENT,
        payment=payment, payment_token=payment_token, amount=payment.total)

    _gateway_postprocess(transaction, payment)
    return transaction


@require_active_payment
def gateway_charge(
        payment: Payment, payment_token: str,
        amount: Decimal = None) -> Transaction:
    """Performs authorization and capture in a single run.

    For gateways not supporting the authorization it should be a
    dedicated CHARGE transaction.

    For gateways not supporting capturing without authorizing,
    it should create two transaction - auth and capture, but only the last one
    is returned.
    """
    if amount is None:
        amount = payment.get_charge_amount()
    clean_charge(payment, amount)

    transaction = call_gateway(
        operation_type=OperationType.CHARGE,
        payment=payment, payment_token=payment_token, amount=amount)

    _gateway_postprocess(transaction, payment)
    return transaction


@require_active_payment
def gateway_authorize(payment: Payment, payment_token: str) -> Transaction:
    """Authorizes the payment and creates relevant transaction.

    Args:
     - payment_token: One-time-use reference to payment information.
    """
    clean_authorize(payment)

    return call_gateway(
        operation_type=OperationType.AUTH,
        payment=payment, payment_token=payment_token)


@require_active_payment
def gateway_capture(payment: Payment, amount: Decimal = None) -> Transaction:
    """Captures the money that was reserved during the authorization stage."""
    if amount is None:
        amount = payment.get_charge_amount()
    clean_capture(payment, amount)

    auth_transaction = payment.transactions.filter(
        kind=TransactionKind.AUTH, is_success=True).first()
    if auth_transaction is None:
        raise PaymentError('Cannot capture unauthorized transaction')
    payment_token = auth_transaction.token

    transaction = call_gateway(
        operation_type=OperationType.CAPTURE,
        payment=payment, payment_token=payment_token, amount=amount)

    _gateway_postprocess(transaction, payment)
    return transaction


@require_active_payment
def gateway_void(payment) -> Transaction:
    if not payment.can_void():
        raise PaymentError('Only pre-authorized transactions can be voided.')

    auth_transaction = payment.transactions.filter(
        kind=TransactionKind.AUTH, is_success=True).first()
    if auth_transaction is None:
        raise PaymentError('Cannot void unauthorized transaction')
    payment_token = auth_transaction.token

    transaction = call_gateway(
        operation_type=OperationType.VOID,
        payment=payment, payment_token=payment_token)

    _gateway_postprocess(transaction, payment)
    return transaction


@require_active_payment
def gateway_refund(payment, amount: Decimal = None) -> Transaction:
    """Refunds the charged funds back to the customer.
    Refunds can be total or partial.
    """
    if amount is None:
        # If no amount is specified, refund the maximum possible
        amount = payment.captured_amount

    if not payment.can_refund():
        raise PaymentError('This payment cannot be refunded.')

    if amount <= 0:
        raise PaymentError('Amount should be a positive number.')
    if amount > payment.captured_amount:
        raise PaymentError('Cannot refund more than captured')

    transaction = payment.transactions.filter(
        kind__in=[TransactionKind.CAPTURE, TransactionKind.CHARGE],
        is_success=True).first()
    if transaction is None:
        raise PaymentError('Cannot refund uncaptured/uncharged transaction')
    payment_token = transaction.token

    transaction = call_gateway(
        operation_type=OperationType.REFUND,
        payment=payment, payment_token=payment_token, amount=amount)

    _gateway_postprocess(transaction, payment)
    return transaction


@require_active_payment
def gateway_transfer(payment, amount: Decimal = None, destination: str = None, transfer_party: TransferParty = None) -> Transfer:
    """Transfers the charged funds to the relevant party (Vendor, Driver etc).
    Transfers can be total or partial.
    """
    if amount is None:
        # If no amount is specified, refund the maximum possible
        amount = payment.captured_amount

    # if not payment.can_transfer():
    #     raise PaymentError('This payment cannot be transfered.')

    if amount <= 0:
        raise PaymentError('Amount should be a positive number.')
    if amount > payment.captured_amount:
        raise PaymentError('Cannot transfer more than captured')

    transfer_from_balance = True
    description = "ORDER #{}".format(payment.order.id)
    transfer_group = "ORDER #{}".format(payment.order.id)
    metadata = {'order_id': payment.order.id}

    if not payment.can_transfer(amount=amount):
        transfer_from_balance = False

    transaction = payment.transactions.filter(
        kind__in=[TransactionKind.CAPTURE, TransactionKind.CHARGE],
        is_success=True).first()
    if transaction is None:
        raise PaymentError('Cannot transfer uncaptured/uncharged transaction')
    payment_token = transaction.token

    transfer = call_gateway(
        operation_type=OperationType.TRANSFER,
        payment=payment,
        payment_token=payment_token,
        amount=amount,
        destination=destination,
        transfer_from_balance=transfer_from_balance,
        description=description,
        metadata=metadata,
        transfer_party=transfer_party,
        transfer_group=transfer_group
    )

    _gateway_postprocess(transfer, payment)
    return transfer
