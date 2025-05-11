from django.contrib import admin
from .models import Category, Item, Delivery, Warehouse, WarehouseInventory


class CategoryAdmin(admin.ModelAdmin):

    list_display = ('name', 'slug')
    search_fields = ('name',)
    ordering = ('name',)


class ItemAdmin(admin.ModelAdmin):
   
    list_display = (
        'name', 'category', 'quantity', 'price', 'expiring_date', 'vendor'
    )
    search_fields = ('name', 'category__name', 'vendor__name')
    list_filter = ('category', 'vendor')
    ordering = ('name',)


class DeliveryAdmin(admin.ModelAdmin):

    list_display = (
        'item', 'warehouse', 'customer_name', 'phone_number',
        'location', 'date', 'is_delivered'
    )
    search_fields = ('item__name', 'customer_name')
    list_filter = ('is_delivered', 'date', 'warehouse')
    ordering = ('-date',)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('warehouse_id', 'name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('warehouse_id', 'name', 'description')
    ordering = ('name',)


@admin.register(WarehouseInventory)
class WarehouseInventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'warehouse', 'quantity', 'location_code', 'min_stock_level', 'max_stock_level', 'is_active')
    list_filter = ('warehouse', 'is_active')
    search_fields = ('item__name', 'warehouse__name', 'location_code')
    ordering = ('warehouse', 'item')
    raw_id_fields = ('item',)


admin.site.register(Category, CategoryAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Delivery, DeliveryAdmin)
