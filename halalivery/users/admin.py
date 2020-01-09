from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
from django.contrib.auth.forms import UserChangeForm
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.mail import EmailMultiAlternatives
from django.contrib.messages.views import SuccessMessageMixin
from . import signals
from halalivery.partner_discounts.models import PartnerDiscount

# import csv
# from django.http import HttpResponse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field

from halalivery.order.models import Order

from django.contrib.gis.db import models
from mapwidgets.widgets import GooglePointFieldWidget

# Customer filter
#from django.contrib.admin import SimpleListFilter



# class ExportCsvMixin:
#     def export_as_csv(self, request, queryset):

#         meta = self.model._meta
#         field_names = [field.name for field in meta.fields]
#         if 'password' in field_names:
#             field_names.remove('password')
#         field_names.append('username')

#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
#         writer = csv.writer(response)

#         writer.writerow(field_names)
#         for obj in queryset:
#             row = writer.writerow([getattr(obj, field) for field in field_names])
#             print(field_names)

#         return response

#     export_as_csv.short_description = "Export Selected"

class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

def send_test_notification(modeladmin, request, queryset):
    for i in queryset:
        for y in range(1, 10):
            print(y)
            i.send_notification("test {}".format(y))
    send_test_notification.short_description = "Send a test notification."

class MyUserAdmin(UserAdmin):
    form = MyUserChangeForm
    actions = ['send_notification', 'send_test_email']
    list_display = ['id', 'username', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('onesignal_token',)}),
    )

    def username(self, obj):
        return obj.user.username
    def first_name(self, obj):
        return obj.user.first_name
    def last_name(self, obj):
        return obj.user.last_name

    def send_notification(self, request, queryset):
        if 'apply' in request.POST:
            if 'notification_text' in request.POST:
                message = request.POST["notification_text"]
                counter = 0
                for counter, user in enumerate(queryset):
                    user.send_notification(message)

                self.message_user(request,
                                  f"Sent message '{message}' to {counter} users.")
                return HttpResponseRedirect(request.get_full_path())

        return render(request, 'admin_notification.html', context={'users': queryset})

    def send_test_email(self, request, queryset):
        for i in queryset:
            msg = EmailMultiAlternatives("Subject", "text body",
                                         "noreply@halalivery.co.uk", ["ax3.mail@gmail.com"])
            msg.attach_alternative("<html>html body</html>", "text/html")
            # you can set any other options on msg here, then...
            msg.send()

admin.site.register(User, MyUserAdmin)


'''
@admin.register(User)
class UserAdmin(UserAdmin):
    pass
'''

# class MyDriverChangeForm(UserChangeForm):
#     class Meta(UserChangeForm.Meta):
#         model = Driver
#         fields = ('id',)
#         extra_kwargs = {'password': {'write_only': True}}


#admin.site.register(Driver, MyDriverAdmin)

# @admin.register(Driver)
# class DriverAdmin(admin.ModelAdmin):
#     pass

class CustomerResource(resources.ModelResource):
    id = Field(attribute='id', column_name='customer_id')
    user_id = Field(attribute='user__id', column_name='user_id')
    username = Field(attribute='user__username', column_name='username')
    first_name = Field(attribute='user__first_name', column_name='first_name')
    last_name = Field(attribute='user__last_name', column_name='last_name')
    email = Field(attribute='user__email', column_name='email')

    class Meta:
        model = Customer
        exclude = ('avatar', 'address', 'payment_token', 'user')
        export_order = ('id', 'user_id', 'username', 'first_name', 'last_name', 'email')
        #fields = ('id', 'username','user__first_name', 'user__last_name', 'user__email')

class DriverResource(resources.ModelResource):
    id = Field(attribute='id', column_name='driver_id')
    user_id = Field(attribute='user__id', column_name='user_id')
    username = Field(attribute='user__username', column_name='username')
    first_name = Field(attribute='user__first_name', column_name='first_name')
    last_name = Field(attribute='user__last_name', column_name='last_name')
    email = Field(attribute='user__email', column_name='email')

    class Meta:
        model = Customer
        exclude = ('avatar', 'address', 'payment_token', 'user')
        export_order = ('id', 'user_id', 'username', 'first_name', 'last_name', 'email')
        #fields = ('id', 'username','user__first_name', 'user__last_name', 'user__email')


@admin.register(Driver)
class DriverAdmin(ImportExportModelAdmin):
    # form = MyDriverChangeForm
    actions = ['send_notification', 'send_zego_email', 'send_credentials_email', 'send_credentials_and_zego_email']
    list_display = ['id', 'username', 'phone', 'first_name', 'last_name', 'online', 'insurance_type', 'transport_type', 'last_location']
    ordering = ['id']
    list_select_related = ('user', 'address')
    resource_class = DriverResource
    def username(self, obj):
        return obj.user.username
    def first_name(self, obj):
        return obj.user.first_name
    def last_name(self, obj):
        return obj.user.last_name
    def phone(self, obj):
        if obj.address:
            return obj.address.phone
        else:
            return ''

    def last_location(self, obj):
        return obj.get_last_location()

    def send_zego_email(self, request, queryset):
        if request.method == 'POST' and 'apply' in request.POST:
            for counter, driver in enumerate(queryset):
                signals.driver_zego_signal(sender=None, driver=driver)
            self.message_user(request, "Successfully sent emails")
            return HttpResponseRedirect(request.get_full_path())

        return render(request, 'admin_driver_zego_email.html', context={'drivers': queryset})

    def send_credentials_email(self, request, queryset):
        if request.method == 'POST' and 'apply' in request.POST and 'password' in request.POST:
            passwords = request.POST.getlist('password')
            for counter, driver in enumerate(queryset):
                username = driver.user.username
                password = passwords[counter]
                signals.driver_credentials_signal(sender=None, driver=driver, username=username, password=password)
            self.message_user(request, "Successfully credentials emails")
            return HttpResponseRedirect(request.get_full_path())
        return render(request, 'admin_driver_credentials.html', context={'drivers': queryset})

    def send_credentials_and_zego_email(self, request, queryset):
        if request.method == 'POST' and 'apply' in request.POST and 'password' in request.POST:
            passwords = request.POST.getlist('password')
            for counter, driver in enumerate(queryset):
                username = driver.user.username
                password = passwords[counter]
                signals.driver_credentials_with_zego_signal(sender=None, driver=driver, username=username, password=password)
            self.message_user(request, "Successfully sent credentials with zego emails")
            return HttpResponseRedirect(request.get_full_path())
        return render(request, 'admin_driver_credentials_with_zego.html', context={'drivers': queryset })

    def send_notification(self, request, queryset):
        if 'apply' in request.POST:
            if 'notification_text' in request.POST:
                message = request.POST["notification_text"]
                counter1 = 0
                for counter, driver in enumerate(queryset):
                    driver.send_notification(message)
                    counter1 = counter + 1
                self.message_user(request,
                                  f"Sent message '{message}' to {counter1} users.")
                return HttpResponseRedirect(request.get_full_path())
        return render(request, 'admin_notification.html', context={'users': queryset})


class OrdersFilter(admin.SimpleListFilter):
    title = 'placed orders' # or use _('country') for translated title
    parameter_name = 'order'

    def lookups(self, request, model_admin):
        #countries = set([c.country for c in model_admin.model.objects.all()])
        #return [(c.id, c.name) for c in countries] + [
         # ('AFRICA', 'AFRICA - ALL')]
        return [('Placed 1 order', 'Placed 1 order'), ('Placed 2 orders', 'Placed 2 orders'), ('Placed more than 2 orders', 'Placed more than 2 orders'), ('Not placed any orders', 'Not placed any orders')]

    def queryset(self, request, queryset):
        if self.value() == 'Placed 1 order':
            orders = Order.objects.filter(customer__in=queryset)
            print(orders)
            return queryset.filter(order_customer__customer__in=queryset)
        #     #return queryset.filter(country__continent='Africa')
            
        #     #orders = Order.objects.filter(customer)
        #     #customers = 
        #orders = Order.objects.filter(customer__in=queryset.first())
        # print(orders)
        # print(orders.count())
            
        #     return queryset.filter() #queryset.filter(user__in=Order.objects.all())#.filter(user__username__in=Order.objects.filter(customer=self))
        
        # # if self.value():
        # #     return queryset.filter(country__id__exact=self.value())
        # return queryset.all()
        return queryset

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name']
    ordering = ['-id']
    list_select_related = ('user',)
    list_filter = (OrdersFilter,)
    resource_class = CustomerResource
    # actions = ["export_admin_action"]

    # fields = ['user', 'address', 'payment_token', 'avatar']
    # readonly_fields = ['address', 'payment_token', 'avatar']

    def username(self, obj):
        return obj.user.username
    def first_name(self, obj):
        return obj.user.first_name
    def last_name(self, obj):
        return obj.user.last_name
    
    
    # def phone(self, obj):
    #     #.prefetch_related('address__phone')
    #     #customer = obj.__class__.objects.get(id=obj.id)
    #     if obj.address:
    #         print(obj.ddress.phone)
    #         #print(obj.customer_address.phone)
    #         return obj.address.phone
    #     else:
    #         return ''

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.PointField: {"widget": GooglePointFieldWidget}
    }
    pass

@admin.register(PaymentToken)
class PaymentTokenAdmin(admin.ModelAdmin):
    pass
