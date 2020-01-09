from django.contrib import admin

# Register your models here.


# class BasketResource(resources.ModelResource):
#     # order_id = Field(attribute='id', column_name='order_id')
#     customer_id = Field(attribute='customer__id', column_name='customer_id')
#     # user_id = Field(attribute='customer__user__id', column_name='user_id')
#     username = Field(attribute='customer__user__username', column_name='username')
#     first_name = Field(attribute='customer__user__first_name', column_name='first_name')
#     last_name = Field(attribute='customer__user__last_name', column_name='last_name')
#     email = Field(attribute='customer__user__email', column_name='email')
#     # address = Field(attribute='address', column_name='customer_order_address')
#     # postcode = Field(attribute='address__postcode', column_name='customer_order_postcode')
#     vendor_id = Field(attribute='vendor__id', column_name='vendor_id')
#     vendor_name = Field(attribute='vendor', column_name='vendor_name')
#     subtotal = Field()
#     total = Field()
#     # driver_id = Field(attribute='driver_id', column_name='driver_id')
#     # driver_first_name = Field(attribute='driver__user__first_name', column_name='driver_first_name')
#     # driver_last_name = Field(attribute='driver__user__last_name', column_name='driver_last_name')
#     # driver_email = Field(attribute='driver__user__email', column_name='driver_email')

#     def dehydrate_total(self, basket):
#         return '%s' % (basket.get_total())

#     def dehydrate_subtotal(self, basket):
#         return '%s' % (basket.get_subtotal())
#     # def before_export(self, queryset):
#     #     for basket in queryset:
#     #         print(self)
#     #         self['total'] = basket.get_total()

#     class Meta:
#         model = Basket
#         #exclude = ('customer', 'vendor', 'driver')
#         # export_order = ('order_id', 'customer_id', 'user_id', 'username', 'first_name', 'last_name', 'email',
#         #                'vendor_id', 'vendor_name', 'driver_id', 'driver_first_name', 'driver_last_name', 'driver_email')
#         # fields = ('id', 'username','user__first_name', 'user__last_name', 'user__email')


# class BasketItemsInlineAdmin(admin.StackedInline):
#     model = BasketItem
#     extra = 0
#     fields = ['item', 'mods', 'quantity']
#     readonly_fields = ['item', 'mods', 'quantity']
#     # 'mods',
#     # def get_queryset(self, request):
#     #     return super().get_queryset(request).select_related('customer', 'vendor', 'address', 'driver', 'voucher', 'partner_discount').prefetch_related('items')

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('item', 'basket').prefetch_related('mods')

# @admin.register(Basket)
# class BasketAdmin(ImportExportActionModelAdmin):
#     fields = ['customer', 'customer_full_name', 'customer_email', 'vendor', 'subtotal',
#               'discount_amount', 'total', 'note', 'created_at', 'updated_at', 'voucher', 'partner_discount']
#     readonly_fields = ['customer', 'customer_full_name', 'customer_email', 'vendor',
#                        'subtotal', 'discount_amount', 'total', 'note', 'created_at', 'updated_at']
#     list_select_related = ('customer__user', 'address', 'vendor', 'voucher', 'partner_discount')
#     inlines = (BasketItemsInlineAdmin,)
#     list_display = ('id', 'customer', 'customer_full_name', 'customer_email',
#                     'vendor', 'delivery_type', 'driver_tip', 'created_at', 'updated_at')
#     list_filter = ('vendor', 'delivery_type', 'driver_tip', 'created_at', 'updated_at')
#     search_fields = ('id', 'customer__user__first_name', 'customer__user__last_name', 'vendor__vendor_name')
#     resource_class = BasketResource

#     def customer_email(self, obj):
#         return '{}'.format(obj.customer.user.email)

#     def customer_full_name(self, obj):
#         return '{} - {}'.format(obj.customer.user.first_name, obj.customer.user.last_name)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('customer', 'vendor')

#     def subtotal(self, obj):
#         return obj.get_subtotal()

#     def discount_amount(self, obj):
#         return obj.get_discount_amount()

#     def total(self, obj):
#         return obj.get_total()

# class BasketItemsModsInlineAdmin(admin.StackedInline):
#     model = BasketItemMod
#     extra = 0

# @admin.register(BasketItem)
# class BasketItemAdmin(admin.ModelAdmin):
#     fields = ['basket', 'item', 'quantity']
#     inlines = (BasketItemsModsInlineAdmin,)
