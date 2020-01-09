from django.contrib import admin

from .models import (Payment, Transaction, Transfer)
# Register your models here.
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    pass

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    pass