from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe

from decimal import Decimal

from django.conf import settings
from halalivery.helpers import get_upload_path
from django_prices.models import MoneyField, TaxedMoneyField


# Create your models here.
class MenuItemOption(models.Model):
    name = models.CharField(max_length=80)
    price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))

    def __str__(self):
        return "{} {} - £{}".format(self.id, self.name, self.price)

    def get_price(self):
        return self.price

class MenuOptionsGroup(models.Model):
    name = models.CharField(max_length=50, null=True, blank=False)
    items = models.ManyToManyField(MenuItemOption, blank=True, related_name="item_group")
    multiple = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    required = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return "ID: {} - {}".format(self.id, self.name)

class MenuItem(models.Model):
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, null=True, blank=True)
    options = models.ManyToManyField(MenuOptionsGroup, blank=True, related_name="menu_options_group")
    price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=Decimal(0.00))
    available = models.BooleanField(default=True)
    popular = models.BooleanField(default=False)
    menu_category = models.ForeignKey(
        'MenuCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Menu Category',
        related_name='items'
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    image = models.ImageField(upload_to=get_upload_path, blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.price, self.description)

    def get_price(self):
        return self.price

    class Meta:
        ordering = ['sort_order', 'name']

class MenuCategory(models.Model):
    name = models.CharField(max_length=50, null=True, blank=False)
    description = models.CharField(max_length=200, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    top_level = models.BooleanField(default=True)
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE, null=True,
                             blank=True, related_name='categories')

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return "{} - {}".format(self.name, self.menu)

    def edit_items(self):
        if self.pk:
            url = reverse('admin:%s_%s_change' % (
                self._meta.app_label, self._meta.model_name), args=[self.pk])
            items_qty = self.items.count()
            return mark_safe(u'<a href="{}">Edit items ({})</a>'.format(url, items_qty))
        else:
            return ''

class Menu(models.Model):
    name = models.CharField(max_length=50)
    items = models.ManyToManyField(MenuItem, related_name="related_menu", blank=True)

    def __str__(self):
        return "{}".format(self.name)
