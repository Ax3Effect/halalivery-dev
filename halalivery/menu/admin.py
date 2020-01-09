from django.contrib import admin
from .models import *
from django.shortcuts import redirect, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms

class MenuCategoryInline(admin.TabularInline):
    extra = 0
    model = MenuCategory
    fields = ('name', 'description', 'sort_order', 'top_level', 'menu', 'edit_items')
    readonly_fields = ('edit_items',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('menu__items', 'menu__items__options', 'menu__items__options__items')

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    class Meta:
        model = Menu

    # fields = ('name', 'items')
    fields = ('name', 'items')
    raw_id_fields = ["items"]
    # list_select_related = ('menu',)
    inlines = (MenuCategoryInline,)
    list_filter = ('id', 'name',)
    # list_editable = ('name',)
    # list_display_links = ('name',)
    # list_display = ('name',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'menu_item_image', 'name', 'marketplace', 'menu_category', 'available', 'price']
    ordering = ['menu_category__menu__name', 'name']
    list_select_related = ['menu_category', 'menu_category__menu']
    list_filter = ('menu_category__menu__name', 'available', 'price')
    search_fields = ['id', 'name', 'description', 'menu_category__menu__name', 'price', 'available']
    filter_horizontal = ('options', )
    # raw_id_fields = ["options"]

    def marketplace(self, obj):
        if obj.menu_category and obj.menu_category.menu:
            return obj.menu_category.menu.name
        else:
            return 'Not asssigned to a menu category'

    readonly_fields = ["menu_item_image", ]

    def menu_item_image(self, obj):
        if obj.image:
            return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
                url=obj.image.url,
                width=100,
                height=150
            )
            )
        return 'No image'

    # def get_queryset(self, request):
    #     print (self)
    #     qs = super(MenuItemAdmin, self).get_queryset(request)
    #     # if request.user.is_superuser:
    #     #     return qs
    #     print(qs.__dict__)
    #     return qs

@admin.register(MenuOptionsGroup)
class MenuOptionsGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'multiple']
    ordering = ['id', 'name', 'multiple']
    list_filter = ('id', 'name', 'multiple')
    search_fields = ['id', 'name']
    filter_horizontal = ('items', )
    #list_editable = ('items',)
    #items = MenuOptionsGroup.items.through
    # inlines = [MenuOptionsGroupItemInline]

@admin.register(MenuItemOption)
class MenuItemOptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price']
    ordering = ['id', 'name', 'price']
    search_fields = ['id', 'name', 'price']
    # def marketplace(self, obj):
    #     if obj.menu_category and obj.menu_category.menu:
    #         return obj.menu_category.menu.name
    #     else:
    #         return 'Not asssigned to a menu category'

class ItemOptionsInline(admin.StackedInline):
    extra = 0
    model = MenuOptionsGroup

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        # widgets = {
        #     'options': forms.MultiValueField(fields=MenuOptionsGroup.objects.all())
        # }
        fields = ['name', 'options']

class ItemInline(admin.StackedInline):
    extra = 0
    model = MenuItem
    # form = MenuItemForm
    # show_change_link = False
    #fields = ["get_edit_link", "name", "image", "options"]
    #readonly_fields = ["get_edit_link"]
    can_delete = True
    show_change_link = True
    #list_editable = ('options',)
    filter_horizontal = ('options', )
    # raw_id_fields = ('options',)

    # def get_edit_link(self, obj=None):
    #     # print(obj.options.all())
    #     if obj.pk:  # if object has already been saved and has a primary key, show link to it
    #         url = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
    #         return mark_safe(u'<a href="{url}">{text}</a>'.format(
    #             url=url,
    #             text="Edit this %s separately" % obj._meta.verbose_name,
    #         ))
    #     return "(save and continue editing to create a link)"
    # get_edit_link.short_description="Edit link"
    # get_edit_link.allow_tags=True

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    inlines = (ItemInline,)
    #form = MenuItemForm2
    # filter_horizontal = ('options',)
    fields = ('name', 'description', 'sort_order', 'top_level', 'menu')

    def response_post_save_change(self, request, obj):
        menu = obj.menu
        if not menu:
            url = reverse('admin:%s_%s_changelist' % (obj._meta.app_label, obj._meta.model_name))
            return redirect(url)
        url = reverse('admin:%s_%s_change' % (obj._meta.app_label, menu._meta.model_name), args=[menu.pk])
        return redirect(url)
