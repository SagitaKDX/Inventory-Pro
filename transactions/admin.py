from django.contrib import admin
from .models import Sale, SaleDetail, Purchase


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
  
    list_display = (
        'id',
        'customer',
        'date_added',
        'grand_total',
        'amount_paid',
        'amount_change'
    )
    search_fields = ('customer__name', 'id')
    list_filter = ('date_added', 'customer')
    ordering = ('-date_added',)
    readonly_fields = ('date_added',)
    date_hierarchy = 'date_added'

    def save_model(self, request, obj, form, change):
       
        super().save_model(request, obj, form, change)


@admin.register(SaleDetail)
class SaleDetailAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'sale',
        'item',
        'price',
        'quantity',
        'total_detail'
    )
    search_fields = ('sale__id', 'item__name')
    list_filter = ('sale', 'item')
    ordering = ('sale', 'item')

    def save_model(self, request, obj, form, change):
      
        super().save_model(request, obj, form, change)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
  
    list_display = (
        'slug',
        'item',
        'warehouse',
        'vendor',
        'order_date',
        'delivery_date',
        'quantity',
        'price',
        'total_value',
        'delivery_status'
    )
    search_fields = ('item__name', 'vendor__name', 'slug', 'warehouse__name')
    list_filter = ('order_date', 'vendor', 'delivery_status', 'warehouse')
    ordering = ('-order_date',)
    readonly_fields = ('total_value',)

    def save_model(self, request, obj, form, change):
     
        obj.total_value = obj.price * obj.quantity
        super().save_model(request, obj, form, change)
