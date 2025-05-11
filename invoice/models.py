from django.db import models
from django_extensions.db.fields import AutoSlugField

from store.models import Item, Warehouse


class Invoice(models.Model):   

    slug = AutoSlugField(unique=True, populate_from='date')
    date = models.DateTimeField(
        auto_now=True,
        verbose_name='Date (e.g., 2022/11/22)'
    )
    customer_name = models.CharField(max_length=30)
    contact_number = models.CharField(max_length=13)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    price_per_item = models.FloatField(verbose_name='Price Per Item (VND)')
    quantity = models.FloatField(default=0.00)
    shipping = models.FloatField(verbose_name='Shipping and Handling')
    total = models.FloatField(
        verbose_name='Total Amount (VND)', editable=False
    )
    grand_total = models.FloatField(
        verbose_name='Grand Total (VND)', editable=False
    )

    def save(self, *args, **kwargs):
        
        self.total = round(self.quantity * self.price_per_item, 2)
        self.grand_total = round(self.total + self.shipping, 2)
        return super().save(*args, **kwargs)

    def __str__(self):
        warehouse_info = f" ({self.warehouse.name})" if self.warehouse else ""
        return f"{self.customer_name}{warehouse_info} - {self.date.strftime('%Y-%m-%d')}"
