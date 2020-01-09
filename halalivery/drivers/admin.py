from django.contrib import admin
from .models import *


from django.contrib.gis.db import models
from mapwidgets.widgets import GooglePointFieldWidget

# Register your models here.

@admin.register(DriverAvailability)
class DriverAvailabilityAdmin(admin.ModelAdmin):
    pass

@admin.register(DriverPayout)
class DriverPayoutAdmin(admin.ModelAdmin):
    pass

@admin.register(DriverOrderVisibility)
class DriverOrderVisibilityAdmin(admin.ModelAdmin):
    pass

@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.PointField: {"widget": GooglePointFieldWidget}
    }