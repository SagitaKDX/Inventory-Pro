import django_tables2 as tables
from .models import Invoice

class InvoiceTable(tables.Table):
   

    class Meta:
        model = Invoice
        template_name = "django_tables2/semantic.html"
        fields = (
            'date', 'customer_name', 'contact_number', 'item', 'warehouse',
            'price_per_item', 'quantity', 'total'
        )
        order_by = 'date'
