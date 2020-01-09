from django.utils.translation import pgettext_lazy

class VendorType:
    RESTAURANT = 'restaurant'
    GROCERY = 'grocery'

    CHOICES = [
        (RESTAURANT, pgettext_lazy('vendor type', 'Restaurant')),
        (GROCERY, pgettext_lazy('vendor type', 'Grocery'))]