from django.contrib import admin
from .models import *
from mapwidgets.widgets import GooglePointFieldWidget
# Register your models here.


@admin.register(DeliveryPartnerJob)
class DeliveryPartnerJobAdmin(admin.ModelAdmin):
    pass

@admin.register(DeliveryPartnerDriver)
class DeliveryPartnerDriverAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.PointField: {"widget": GooglePointFieldWidget}
    }

@admin.register(DeliveryRoute)
class DeliveryRouteAdmin(admin.ModelAdmin):
    pass
