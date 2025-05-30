import django_tables2 as tables
from .models import Bill


class BillTable(tables.Table):

    class Meta:
        model = Bill
        template_name = "django_tables2/semantic.html"
        fields = (
            'date',
            'institution_name',
            'warehouse',
            'phone_number',
            'email',
            'address',
            'description',
            'payment_details',
            'amount',
            'status'
        )
        order_by_field = 'sort'
