# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.gis import admin
from django import forms
from django.contrib.admin.views.main import ChangeList
from django.contrib.gis.db import models

from .models import *
from halalivery.order.models import *
from halalivery.menu.models import *
from halalivery.basket.models import *
from halalivery.payment.models import *
from halalivery.payment import TransferParty, ChargeStatus
from halalivery.users.models import Driver
from .signals import order_available
from django.shortcuts import redirect, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.contrib import messages
import stripe
from halalivery.static import STRIPE_API_KEY
import threading
from halalivery.marketplaces import signals
import newrelic.agent
import sys

# Import export
from import_export import resources
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from import_export.fields import Field

from decimal import Decimal

from halalivery.drivers.gateways.stuart import StuartClient


# GeoDjango
from ..static import GOOGLE_MAPS_API_KEY


@admin.register(MarketplaceVisibillity)
class MarketplaceVisibillityAdmin(admin.ModelAdmin):
   pass

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'online']
    list_filter = ('vendor', 'online')
    ordering = ['vendor']
    filter_horizontal = ('category', 'operating_times')

@admin.register(Grocery)
class GroceryAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'online']
    list_filter = ('vendor', 'online')
    ordering = ['vendor']
    filter_horizontal = ('category', 'operating_times')

# class GMapPolygonWidget(forms.gis.BaseGMapWidget, forms.gis.PolygonWidget):
#     google_maps_api_key = GOOGLE_MAPS_API_KEY

# class GmapForm(forms.ModelForm):
#     area = forms.gis.PolygonField(widget=GMapPolygonWidget)

@admin.register(ServiceableArea)
class ServiceableAreaAdmin(admin.OSMGeoAdmin):
    pass
    #form = GmapForm

@admin.register(VendorCategory)
class RestaurantCategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(OperatingTime)
class OperatingTimeAdmin(admin.ModelAdmin):
    pass

@admin.register(PrepTime)
class PrepTime(admin.ModelAdmin):
    pass
