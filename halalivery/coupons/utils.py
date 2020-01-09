from decimal import Decimal
from .models import Coupon
from django.db.models import F
from datetime import datetime, timedelta, time, date
from django.utils import timezone

def get_discount_amount(voucher, amount):
    if voucher:
        if voucher.type == 'percentage':
            return (voucher.value / Decimal('100')) * amount
        elif voucher.type == 'monetary':
            return voucher.value
    else:
        return Decimal('0.00')

def increase_voucher_usage(voucher):
    """Increase voucher uses by 1."""
    voucher.used = F('used') + 1
    voucher.save(update_fields=['used'])

def decrease_voucher_usage(voucher):
    """Decrease voucher uses by 1."""
    voucher.used = F('used') - 1
    voucher.save(update_fields=['used'])

# def get_voucher_for_cart(voucher_code, vouchers=None):
#     """Return voucher with voucher code saved in cart if active or None."""
#     now = timezone.localtime(timezone.now())
#     if voucher_code is not None:
#         if vouchers is None:
#             vouchers = Coupon.objects.active(date=now)
#         try:
#             return vouchers.get(code=voucher_code)
#         except Coupon.DoesNotExist:
#             return None
#     return None

def get_voucher_for_cart(cart, vouchers=None):
    """Return voucher with voucher code saved in cart if active or None."""
    if cart.voucher_code is not None:
        if vouchers is None:
            vouchers = Coupon.objects.active(date=date.today())
        try:
            return vouchers.get(code=cart.voucher_code)
        except Coupon.DoesNotExist:
            return None
    return None