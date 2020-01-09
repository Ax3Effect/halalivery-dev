from django.db import models
from halalivery.users.models import Vendor
from django.utils import timezone
from decimal import Decimal

class PartnerDiscount(models.Model):
    """
    A 20% partner discount
    """
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='partner_discount')
    timestamp = models.DateTimeField(auto_now=True, editable=False)
    expires_on = models.DateTimeField(editable=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=4, decimal_places=2)
    min_amount_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    name = models.CharField(max_length=100, blank=False, null=True)

    def __str__(self):
        return "{} - {}% - {}".format(self.vendor, self.amount, self.expires_on)

    def has_spent_minimum(self, amount=Decimal('0.00')):
        if self.min_amount_spent > amount:
            return False
        elif amount >= self.min_amount_spent:
            return True
        else:
            return False

    def is_valid(self):
        now = timezone.localtime(timezone.now())
        expiration_date = self.expires_on

        if not expiration_date:
            return True
        if expiration_date <= now:
            return False
        else:
            return True
