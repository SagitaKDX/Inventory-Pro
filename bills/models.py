from django.db import models
from autoslug import AutoSlugField
from store.models import Warehouse


class Bill(models.Model):

    slug = AutoSlugField(unique=True, populate_from='date')
    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date (e.g., 2022/11/22)'
    )
    institution_name = models.CharField(
        max_length=30,
        blank=False,
        null=False
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills'
    )
    phone_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Phone number of the institution'
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text='Email address of the institution'
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Address of the institution'
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Description of the bill'
    )
    payment_details = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        help_text='Details of the payment'
    )
    amount = models.FloatField(
        verbose_name='Total Amount Owing (VND)',
        help_text='Total amount due for payment'
    )
    status = models.BooleanField(
        default=False,
        verbose_name='Paid',
        help_text='Payment status of the bill'
    )

    def __str__(self):
        warehouse_info = f" ({self.warehouse.name})" if self.warehouse else ""
        return f"{self.institution_name}{warehouse_info} - {self.date.strftime('%Y-%m-%d')}"
