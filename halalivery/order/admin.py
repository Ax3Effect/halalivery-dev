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
from halalivery.marketplaces.signals import order_available
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
class OrderItemsInlineAdmin(admin.StackedInline):
    model = OrderItem
    # extra = 0
    # # fields = ['item', 'mods', 'quantity']
    # # readonly_fields = ['mods', 'item', 'quantity']
    # def get_queryset(self, request):
    #     # Return all Sleep objects where start_time and end_time are within Diary.day
    #     return OrderItem.objects.filter(order=1)
    # def get_queryset(self, request):
    #     return super().get_queryset(request).select_related('customer', 'vendor', 'address', 'driver', 'voucher', 'partner_discount').prefetch_related('items')

    # def get_queryset(self, request):
    #     return super().get_queryset(request).select_related('item')

    # def formfield_for_manytomany(self, db_field, request, **kwargs):
    #     field = super(OrderItemsInlineAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
    #     if db_field.name == "items" and hasattr(self, "cached_items"):
    #         field.choices = self.cached_items
    #     return field

    # def get_queryset(self, request):
    #     # LIMIT_SEARCH = 25
    #     queryset = super(OrderItemsInlineAdmin, self).get_queryset(request)
    #     ids = queryset.order_by('-id').values('pk')
    #     qs = Order.items.through.objects.filter(pk__in=ids).order_by('-id')
    #     return qs


def cancel_order(modeladmin, request, queryset):
    for obj in queryset:
        if obj.status == 7:
            messages.error(request, "Order #{} has been canceled already".format(obj.id))
            return HttpResponseRedirect(".")

        stripe.api_key = STRIPE_API_KEY
        # if obj.charge != None:
        #     order_charge = get_object_or_404(Charge, id=obj.charge.id)
        #     try:
        #         # Refund a charge
        #         refund = stripe.Refund.create(charge=order_charge.charge_id)
        #         order_charge.refund_id = refund.id
        #         order_charge.status = 3
        #         order_charge.save()
        #     except Exception as e:
        #         exc_info = sys.exc_info()
        #         newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
        #         messages.error(request, "Error: {}".format(e))
        #         return HttpResponseRedirect(".")
        try:
            last_payment = obj.get_last_payment()
            if last_payment.can_refund():
                last_payment.refund()
            else:
                last_payment.void()
        except Exception as e:
            exc_info = sys.exc_info()
            newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
            messages.error(request, "Error: {}".format(e))
            return HttpResponseRedirect(".")
        obj.status = 7
        obj.save()
        signals.order_rejected.send(sender=None, order=obj)
        messages.info(request, "Order #{} has been canceled.".format(obj.id))
    return HttpResponseRedirect(".")


cancel_order.short_description = "Cancel selected orders"

class OrderResource(resources.ModelResource):
    order_id = Field(attribute='id', column_name='order_id')
    customer_id = Field(attribute='customer__id', column_name='customer_id')
    user_id = Field(attribute='customer__user__id', column_name='user_id')
    username = Field(attribute='customer__user__username', column_name='username')
    first_name = Field(attribute='customer__user__first_name', column_name='first_name')
    last_name = Field(attribute='customer__user__last_name', column_name='last_name')
    email = Field(attribute='customer__user__email', column_name='email')
    address = Field(attribute='address', column_name='customer_order_address')
    postcode = Field(attribute='address__postcode', column_name='customer_order_postcode')
    vendor_id = Field(attribute='vendor__id', column_name='vendor_id')
    vendor_name = Field(attribute='vendor', column_name='vendor_name')
    driver_id = Field(attribute='driver_id', column_name='driver_id')
    driver_first_name = Field(attribute='driver__user__first_name', column_name='driver_first_name')
    driver_last_name = Field(attribute='driver__user__last_name', column_name='driver_last_name')
    driver_email = Field(attribute='driver__user__email', column_name='driver_email')
    total = Field(attribute='total', column_name='total')

    class Meta:
        model = Order
        exclude = ('customer', 'vendor', 'driver')
        export_order = ('order_id', 'customer_id', 'user_id', 'username', 'first_name', 'last_name', 'email',
                        'vendor_id', 'vendor_name', 'driver_id', 'driver_first_name', 'driver_last_name', 'driver_email')
        # fields = ('id', 'username','user__first_name', 'user__last_name', 'user__email')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    pass

@admin.register(Order)
class OrderAdmin(ImportExportActionModelAdmin):
    fields = ['customer', 'customer_full_name', 'vendor', 'driver', 'delivery_fee', 'delivery_type', 'delivery_by', 'delivery_address', 'status', 'prep_time', 'created_at', 'time_placed', 'updated_at',
              'subtotal', 'surcharge', 'voucher', 'discount_amount', 'total', 'driver_tip', 'customer_note', 'vendor_profit', 'driver_profit']
    inlines = (OrderItemsInlineAdmin,)
    list_filter = ('status', 'vendor', 'time_placed', 'updated_at')
    ordering = ('-id', 'status')
    search_fields = ('id', 'customer__user__first_name', 'customer__user__last_name', 'vendor__vendor_name')
    list_select_related = ('customer__user', 'delivery_address', 'vendor')
    list_display = ['id', 'status', 'first_name', 'last_name',
                    'vendor', 'delivery_address', 'total', 'time_placed', 'updated_at']
    readonly_fields = ['customer_full_name', 'vendor', 'prep_time', 'surcharge', 'delivery_fee',
    'delivery_address', 'billing_address',
                        'subtotal', 'voucher', 'discount_amount', 'total', 'customer_note', 'vendor_profit', 'driver_profit', 'driver_tip', 'created_at', 'updated_at', 'time_placed']
    change_form_template = "order_templates/order_admin.html"
    actions = [cancel_order]
    resource_class = OrderResource

    # matching_names_except_this = self.get_queryset(request).filter(name=obj.name).exclude(pk=obj.id)
    # matching_names_except_this.delete()
    # obj.is_unique = True
    # obj.save()
    def response_change(self, request, obj):
        if "_accept_order" in request.POST:
            if obj.status < 1:
                messages.error(request, "Order is not confirmed. Most likely its not paid for.")
                return HttpResponseRedirect(".")
            elif obj.status > 1:
                messages.error(request, "Order has been accepted already.")
                return HttpResponseRedirect(".")
            elif obj.status == 7 and obj.charge != None:
                messages.error(request, "Order has been canceled and refunded.")
                return HttpResponseRedirect(".")

            if request.POST['_delivery_type'] == 'halalivery':
                obj.delivery_type = 0
            elif request.POST['_delivery_type'] == 'vendor':
                obj.delivery_type = 1
            elif request.POST['_delivery_type'] == 'self_pickup':
                obj.delivery_type = 2

            # order_charge = get_object_or_404(Charge, id=obj.charge.id)
            # stripe.api_key = STRIPE_API_KEY
            try:
                # # Retreive a charge
                # charge = stripe.Charge.retrieve(order_charge.charge_id)
                # # Capture the charge
                # charge.capture()

                # order_charge.charge_id = charge.id
                # order_charge.status = 1
                # order_charge.save()

                # obj.status = 2
                # obj.save()

                # Process the payment
                last_payment = obj.get_last_payment()
                last_payment.charge(payment_token=last_payment.get_last_transaction().token,
                                    amount=last_payment.get_last_transaction().amount)

                obj.status = OrderStatus.PREPARING
                obj.save()
                # Send push notifications to available drivers only if its Halalivery delivery
                if request.POST['_delivery_type'] == 'halalivery':
                    # send_push_notifications_available_drivers.delay(order_id=obj.id)
                    # Notify on slack about halalivery delivery selected
                    signals.vendor_delivery_halalivery.send(sender=None, order=obj, vendor=obj.vendor)
                elif request.POST['_delivery_type'] == 'vendor':
                    # Notify on slack about vendor delivery selected
                    signals.vendor_delivery_own_signal(sender=None, order=obj, vendor=obj.vendor)

                # Notify user about order acceptance
                signals.order_accepted.send(sender=None, customer=obj.customer, order=obj)
                self.message_user(request, "The order has been accepted.")
                return HttpResponseRedirect(".")
            except stripe.error.CardError as e:
                exc_info = sys.exc_info()
                newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                messages.error(request, "There was an issue with the customer\'s payment details. {}".format(e))
                return HttpResponseRedirect(".")
            except stripe.error.StripeError as e:
                exc_info = sys.exc_info()
                newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                messages.error(request, "Stripe error: {}".format(e))
                return HttpResponseRedirect(".")
            except Exception as e:
                exc_info = sys.exc_info()
                newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                messages.error(request, "Unknown error: {}".format(e))
                return HttpResponseRedirect(".")
        elif "_prepare_order" in request.POST:
            if obj.status < 2:
                messages.error(request, "Order has not been accepted")
                return HttpResponseRedirect(".")

            elif obj.status > 2:
                messages.error(request, "Order has been prepared already.")
                return HttpResponseRedirect(".")

            # order_transfer = get_object_or_404(Transfer,id=obj.transfer.id)
            # order_charge = get_object_or_404(Charge, id=obj.charge.id)
            vendor_total = vendor_order_total(order=obj)

            if obj.delivery_type == DeliveryType.HALALIVERY or obj.delivery_type == DeliveryType.SELF_PICKUP:

                # try:
                #     # Vendor Transfer
                #     stripe.api_key = STRIPE_API_KEY
                #     # if a discount used
                #     if vendor_total > obj.total:
                #         transfer = stripe.Transfer.create(
                #             amount=int(vendor_total * 100),
                #             currency="gbp",
                #             description="ORDER #{}".format(obj.id),
                #             metadata={'order_id': obj.id},
                #             destination="{}".format(obj.vendor.stripe_connect_id),
                #             transfer_group="ORDER #{}".format(obj.id),
                #         )
                #         order_transfer.vendor_transfer_id = transfer.id
                #         order_transfer.save()
                #     elif vendor_total <= obj.total:
                #         transfer = stripe.Transfer.create(
                #             amount=int(vendor_total * 100),
                #             currency="gbp",
                #             description="ORDER #{}".format(obj.id),
                #             metadata={'order_id': obj.id},
                #             source_transaction=order_charge.charge_id,
                #             destination="{}".format(obj.vendor.stripe_connect_id),
                #             transfer_group="ORDER #{}".format(obj.id),
                #         )
                #         order_transfer.vendor_transfer_id = transfer.id
                #         order_transfer.save()
                # except Exception as e:
                #     exc_info = sys.exc_info()
                #     newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                #     messages.error(request, "Error: {}".format(e))
                #     return HttpResponseRedirect(".")
                try:
                    last_payment = obj.get_last_payment()
                    last_payment.transfer(
                        amount=vendor_total, destination=obj.vendor.stripe_connect_id, transfer_party=TransferParty.VENDOR)
                                    # Send a job to Stuart
                except Exception as e:
                    exc_info = sys.exc_info()
                    newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                    messages.error(request, "Error: {}".format(e))
                    return HttpResponseRedirect(".")
            obj.status = OrderStatus.READY_FOR_PICKUP
            obj.save()

            if obj.delivery_type == DeliveryType.SELF_PICKUP:
                signals.order_ready_for_self_pickup.send(sender=None, order=obj)
            elif obj.delivery_type == DeliveryType.HALALIVERY:
                StuartClient().create_job(obj)
                if obj.driver != None:
                    signals.order_ready_for_pickup.send(sender=None, order=obj)
                else:
                    pass
                    # No need to send a notification there is a background worker
                    # send_push_notifications_available_drivers.delay(order_id=obj.id)
                    # send notification to everyone

            # if obj.driver is None:
            signals.vendor_prepared_order.send(sender=None, order=obj, vendor=obj.vendor)
            self.message_user(request, "The order has been prepared.")
            return HttpResponseRedirect(".")
        elif "_picked_order" in request.POST:
            if obj.status < 3:
                messages.error(request, "Order has not been prepared.")
                return HttpResponseRedirect(".")
            # elif order.delivery_type == 2 and order.status == 8:
            #     messages.error(request, "Order has been picked up by the customer."))
            #     return HttpResponseRedirect(".")
            # elif order.delivery_type == 1 and order.status >= 5:
            #     messages.error(request, "Order has been picked up by the driver."))
            #     return HttpResponseRedirect(".")
            # elif order.delivery_type == 0:
            #     messages.error(request, "Order will be picked up by the Halalivery driver."))
            #     return HttpResponseRedirect(".")

            # self pickup
            if obj.delivery_type == 2:
                obj.status = 8

            # own driver
            elif obj.delivery_type <= 1:
                obj.status = 5
                signals.driver_collected.send(sender=None, customer=obj.customer, order=obj)

            obj.save()
            self.message_user(request, "The order has been picked up.")
            return HttpResponseRedirect(".")
        elif "_delivered_order" in request.POST:
            if obj.status > 5:
                messages.error(request, "Order has been delivered already.")
                return HttpResponseRedirect(".")
            elif obj.status < 5:
                messages.error(request, "Order has not been picked by the driver.")
                return HttpResponseRedirect(".")
            if obj.delivery_type == 2:
                messages.error(request, "Order delivery type is self_pickup. Order cannot be delivered.")
                return HttpResponseRedirect(".")

            if obj.delivery_type == 1:
                try:
                    last_payment = obj.get_last_payment()
                    vendor_total = vendor_order_total(order=obj)
                    last_payment.transfer(
                        amount=vendor_total, destination=obj.vendor.stripe_connect_id, transfer_party=TransferParty.VENDOR)
                except Exception as e:
                    exc_info = sys.exc_info()
                    newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                    messages.error(request, "Error: {}".format(e))
                    return HttpResponseRedirect(".")
            elif obj.delivery_type == DeliveryType.HALALIVERY and obj.driver != None:
                driver_total = driver_order_total(order=obj)
                try:
                    last_payment = obj.get_last_payment()
                    last_payment.transfer(
                        amount=driver_total, destination=obj.driver.stripe_connect_id, transfer_party=TransferParty.DRIVER)
                except Exception as e:
                    exc_info = sys.exc_info()
                    newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                    messages.error(request, "Error: {}".format(e))
                    return HttpResponseRedirect(".")

            obj.status = OrderStatus.DRIVER_DELIVERED
            obj.save()
            signals.order_delivered.send(sender=None, order=obj)
            self.message_user(request, "The order has been delivered.")
            return HttpResponseRedirect(".")
        elif "_cancel_order" in request.POST:
            if obj.status == OrderStatus.CANCELED:
                messages.error(request, "Order #{} has been canceled already".format(obj.id))
                return HttpResponseRedirect(".")

            try:
                last_payment = obj.get_last_payment()
                if last_payment.can_refund():
                    last_payment.refund()
                else:
                    last_payment.void()
            except Exception as e:
                exc_info = sys.exc_info()
                newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
                messages.error(request, "Error: {}".format(e))
                return HttpResponseRedirect(".")
            obj.status = OrderStatus.CANCELED
            obj.save()
            signals.order_rejected.send(sender=None, order=obj)
            self.message_user(request, "Order #{} has been canceled.".format(obj.id))
            # if 'confirm_order_cancel' in request.POST:
            #     print('yes cancel it')
            # #         if 'notification_text' in request.POST:
            # #             message = request.POST["notification_text"]
            # #             counter1 = 0
            # #             for counter, driver in enumerate(queryset):
            # #                 driver.send_notification(message)
            # #                 counter1 = counter + 1
            # #             self.message_user(request,
            # #                             f"Sent message '{message}' to {counter1} users.")
            # #             return HttpResponseRedirect(request.get_full_path())
            return HttpResponseRedirect(".")
            # return render(request, 'order_templates/confirm_order_cancel.html', context={'order': obj})
        return super().response_change(request, obj)

    def get_total(self, obj):
        return obj.total_balance()

    def vendor_profit(self, obj):
        return ''
       # return '{}'.format(vendor_order_total(obj))

    def driver_profit(self, obj):
        return ''
    # return '{}'.format(driver_order_total(obj))

    def customer_full_name(self, obj):
        return '{} - {}'.format(obj.customer.user.first_name, obj.customer.user.last_name)

    def first_name(self, obj):
        return obj.customer.user.first_name

    def last_name(self, obj):
        return obj.customer.user.last_name

    first_name.admin_order_field = 'customer__user__first_name'
    last_name.admin_order_field = 'customer__user__last_name'

    # def get_queryset(self, request):
    #      #return super().get_queryset(request).select_related('driver', 'customer')#.prefetch_related('driver__user__first_name', 'driver__user__last_name', 'driver__id')#
    #      return super().get_queryset(request).select_related('customer').prefetch_related(Prefetch('customer', queryset=Customer.objects.select_related('user')))

    # def get_queryset(self, request):
    #     queryset = super().get_queryset(request)
    #     queryset = queryset.annotate(
    #         _address='address',
    #         _postcode='address__postcode',
    #         _first_name='customer__user__first_name',
    #         _last_name='customer__user__lastname'

    #     )
    #     return queryset

    # def get_formsets_with_inlines(self, request, obj=None):
    #     for inline in self.get_inline_instances(request, obj):
    #         inline.cached_items = [(i.pk, str(i)) for i in MenuItem.objects.all().prefetch_related('options')]
    #         #inline.cached_menucategories = [(i.pk, str(i)) for i in MenuItemCategory.objects.all()]
    #         yield inline.get_formset(request, obj), inline
