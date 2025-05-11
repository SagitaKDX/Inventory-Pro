from django.db import models
from django_extensions.db.fields import AutoSlugField

from store.models import Item, Warehouse, WarehouseInventory
from accounts.models import Vendor, Customer

def get_default_warehouse():
    return Warehouse.objects.filter(is_active=True).first()

DELIVERY_CHOICES = [("P", "Pending"), ("S", "Successful")]


class Sale(models.Model):
    

    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Sale Date"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.DO_NOTHING,
        db_column="customer"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.DO_NOTHING,
        db_column="warehouse",
        default=get_default_warehouse,
        null=True
    )
    sub_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    tax_percentage = models.FloatField(default=0.0)
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    amount_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )

    class Meta:
        db_table = "sales"
        verbose_name = "Sale"
        verbose_name_plural = "Sales"

    def __str__(self):
        
        return (
            f"Sale ID: {self.id} | "
            f"Grand Total: {self.grand_total} | "
            f"Date: {self.date_added}"
        )

    def sum_products(self):
       
        return sum(detail.quantity for detail in self.saledetail_set.all())


class SaleDetail(models.Model):
   

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        db_column="sale",
        related_name="saledetail_set"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.DO_NOTHING,
        db_column="item"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.DO_NOTHING,
        db_column="warehouse",
        null=True,
        blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    quantity = models.PositiveIntegerField()
    total_detail = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "sale_details"
        verbose_name = "Sale Detail"
        verbose_name_plural = "Sale Details"

    def __str__(self):
       
        return (
            f"Detail ID: {self.id} | "
            f"Sale ID: {self.sale.id} | "
            f"Quantity: {self.quantity}"
        )


class Purchase(models.Model):
  

    slug = AutoSlugField(unique=True, populate_from="vendor")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE,
        related_name="purchases",
        null=True
    )
    description = models.TextField(max_length=300, blank=True, null=True)
    vendor = models.ForeignKey(
        Vendor, related_name="vendor_purchases", on_delete=models.CASCADE
    )
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(
        blank=True, null=True, verbose_name="Delivery Date"
    )
    quantity = models.PositiveIntegerField(default=0)
    delivery_status = models.CharField(
        choices=DELIVERY_CHOICES,
        max_length=1,
        default="P",
        verbose_name="Delivery Status",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name="Price per item (VND)",
    )
    total_value = models.DecimalField(max_digits=10, decimal_places=2)
    _skip_inventory_update = False

    def save(self, *args, **kwargs):
      
        self.total_value = self.price * self.quantity
        if self._skip_inventory_update:
            return super().save(*args, **kwargs)
        is_new = self.pk is None
        if not is_new:
            try:
                original = Purchase.objects.get(pk=self.pk)
                original_quantity = original.quantity
            except Purchase.DoesNotExist:
                original_quantity = 0
        else:
            original_quantity = 0
        quantity_difference = self.quantity - original_quantity
        
        super().save(*args, **kwargs)
        
        if quantity_difference != 0:
            self.item.quantity += quantity_difference
            self.item.save()
            
            if self.warehouse:
                warehouse_inventory, created = WarehouseInventory.objects.get_or_create(
                    item=self.item,
                    warehouse=self.warehouse,
                    defaults={
                        'quantity': quantity_difference,
                        'is_active': True
                    }
                )
                
                if not created:
                    warehouse_inventory.quantity += quantity_difference
                    warehouse_inventory.save()

    def __str__(self):
        warehouse_info = f" at {self.warehouse.name}" if self.warehouse else ""
        return f"{self.item.name}{warehouse_info}"

    class Meta:
        ordering = ["order_date"]
