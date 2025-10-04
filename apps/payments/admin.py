from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "type",
        "borrowing",
        "money_to_pay",
    )
    list_filter = ("status", "type")
    search_fields = ("borrowing__user__email", "borrowing__book__title")
