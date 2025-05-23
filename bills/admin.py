from django.contrib import admin
from .models import Bill


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):

    fields = (
        'date',
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
    )

    list_display = (
        'slug',
        'date',
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
    )
