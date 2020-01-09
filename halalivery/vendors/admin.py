from django.contrib import admin
from halalivery.users.models import Vendor
# Register your models here.

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'phone', 'first_name', 'last_name', 'online']
    ordering = ['id']
    list_select_related = ('user', 'address')

    def online(self, obj):
        return obj.marketplace().online

    def username(self, obj):
        return obj.user.username
    def first_name(self, obj):
        return obj.user.first_name
    def last_name(self, obj):
        return obj.user.first_name
    def phone(self, obj):
        if obj.address:
            return obj.address.phone
        else:
            return ''
