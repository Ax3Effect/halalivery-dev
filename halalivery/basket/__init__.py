import logging

from django.utils.translation import pgettext_lazy

logger = logging.getLogger(__name__)


class AddressType:
    BILLING = 'billing'
    SHIPPING = 'shipping'

    CHOICES = [
        (BILLING, pgettext_lazy(
            'Type of address used to fulfill order',
            'Billing'
        )),
        (SHIPPING, pgettext_lazy(
            'Type of address used to fulfill order',
            'Shipping'
        ))]

class BasketErrorTypes:
    VOUCHER_MINIMUM_SPENT = "VOUCHER_MINIMUM_SPENT"
    VOUCHER_NOT_APPLICABLE = "VOUCHER_NOT_APPLICABLE"
    VOUCHER_NOT_FOUND = "VOUCHER_NOT_FOUND"
    PARTNER_DISCOUNT_MINIMUM_SPENT = "PARTNER_DISCOUNT_MINIMUM_SPENT"
    PARTNER_DISCOUNT_NOT_APPLICABLE = "PARTNER_DISCOUNT_NOT_APPLICABLE"