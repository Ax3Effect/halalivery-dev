__version__ = '1.2.0a3'
from django.utils.translation import pgettext_lazy

class DiscountType:
    VOUCHER = "VOUCHER"
    PARTNER = "PARTNER"
    FIRST_ORDER = "FIRST_ORDER"
    PROMOTION = "PROMOTION"

    CHOICES = [
        (VOUCHER, pgettext_lazy('Discount type', 'Voucher')),
        (PARTNER, pgettext_lazy('Discount type', 'Partner')),
        (FIRST_ORDER, pgettext_lazy('Discount type', 'First order')),
        (PROMOTION, pgettext_lazy('Discount type', 'Promotion'))]