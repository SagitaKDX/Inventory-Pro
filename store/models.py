from django.db import models
from django.urls import reverse
from django.forms import model_to_dict
from django_extensions.db.fields import AutoSlugField
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import Vendor


class Warehouse(models.Model):
    warehouse_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    class Meta:
        ordering = ['name']
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'


class Category(models.Model):
  
    name = models.CharField(max_length=50)
    slug = AutoSlugField(unique=True, populate_from='name')

    def __str__(self):
        return f"Category: {self.name}"

    class Meta:
        verbose_name_plural = 'Categories'


class Item(models.Model):
   
    slug = AutoSlugField(unique=True, populate_from='name')
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=256)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    price = models.FloatField(default=0)
    expiring_date = models.DateTimeField(null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)

    def __str__(self):
       
        return (
            f"{self.name} - Category: {self.category}, "
            f"Quantity: {self.quantity}"
        )

    def get_absolute_url(self):
      
        return reverse('product-detail', kwargs={'slug': self.slug})

    def to_json(self):
        product = model_to_dict(self)
        product['id'] = self.id
        product['text'] = self.name
        product['category'] = self.category.name
        product['price'] = self.price
        product['quantity'] = 1
        product['total_product'] = 0
        return product

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Items'


class WarehouseInventory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='warehouse_inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventories')
    quantity = models.IntegerField(default=0)
    location_code = models.CharField(max_length=50, blank=True, null=True, help_text="Location code within the warehouse (e.g., Shelf A-12)")
    min_stock_level = models.IntegerField(default=0, help_text="Minimum stock level before reordering")
    max_stock_level = models.IntegerField(default=0, help_text="Maximum stock capacity")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Warehouse Inventory'
        verbose_name_plural = 'Warehouse Inventories'
        unique_together = ('item', 'warehouse')
        ordering = ['warehouse', 'item']
    
    def __str__(self):
        return f"{self.item.name} in {self.warehouse.name} ({self.quantity})"


class Delivery(models.Model):
   
    item = models.ForeignKey(
        Item, blank=True, null=True, on_delete=models.SET_NULL
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True
    )
    customer_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True)
    location = models.CharField(max_length=20, blank=True, null=True)
    date = models.DateTimeField()
    is_delivered = models.BooleanField(
        default=False, verbose_name='Is Delivered'
    )

    def __str__(self):
       
        return (
            f"Delivery of {self.item} to {self.customer_name} "
            f"at {self.location} on {self.date}"
        )
