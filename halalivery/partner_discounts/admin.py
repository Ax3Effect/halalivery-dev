from django.contrib import admin
from halalivery.partner_discounts.models import PartnerDiscount


# Register your models here.
#admin.site.register(PartnerDiscount)

@admin.register(PartnerDiscount)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['id', 'amount', 'vendor', 'expires_on']
    ordering = ['id']