from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

from django.views.generic import (
    DetailView, CreateView, UpdateView, DeleteView
)

from django_tables2 import SingleTableView
from django_tables2.export.views import ExportMixin

from .models import Invoice
from .tables import InvoiceTable

# list of invoices view
class InvoiceListView(LoginRequiredMixin, ExportMixin, SingleTableView):
    
    model = Invoice
    table_class = InvoiceTable
    template_name = 'invoice/invoicelist.html'
    context_object_name = 'invoices'
    paginate_by = 10
    table_pagination = False  

    def get_queryset(self):
        queryset = super().get_queryset()
        view_mode = self.request.GET.get('view_mode', 'all')
        self.view_mode = view_mode
        
        if view_mode == 'current' and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                from store.models import Warehouse
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                queryset = queryset.filter(warehouse=warehouse)
            except Warehouse.DoesNotExist:
                pass
                
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_mode'] = getattr(self, 'view_mode', 'all')
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                from store.models import Warehouse
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                context['current_warehouse'] = warehouse
            except Warehouse.DoesNotExist:
                pass
                
        return context

# invoice detail view
class InvoiceDetailView(DetailView):
    
    model = Invoice
    template_name = 'invoice/invoicedetail.html'

    def get_success_url(self):
        
        return reverse('invoice-detail', kwargs={'slug': self.object.pk})

# create a new invoice
class InvoiceCreateView(LoginRequiredMixin, CreateView):
   
    model = Invoice
    template_name = 'invoice/invoicecreate.html'
    fields = [
        'customer_name', 'contact_number', 'item',
        'price_per_item', 'quantity', 'shipping'
    ]

    def form_valid(self, form):
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            from store.models import Warehouse
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.instance.warehouse = warehouse
            except Warehouse.DoesNotExist:
                pass
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('invoicelist')

# update an existing invoice
class InvoiceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    
    model = Invoice
    template_name = 'invoice/invoiceupdate.html'
    fields = [
        'customer_name', 'contact_number', 'item',
        'price_per_item', 'quantity', 'shipping'
    ]

    def form_valid(self, form):
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            from store.models import Warehouse
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.instance.warehouse = warehouse
            except Warehouse.DoesNotExist:
                pass
        return super().form_valid(form)

    def get_success_url(self):
        
        return reverse('invoicelist')

    def test_func(self):
        
        return self.request.user.is_superuser

# delete an invoice
class InvoiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
   
    model = Invoice
    template_name = 'invoice/invoicedelete.html'
    success_url = '/products'  

    def get_success_url(self):   
        return reverse('invoicelist')

    def test_func(self):
        return self.request.user.is_superuser

@login_required
def export_invoices_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Invoices'
    warehouse_prefix = ""
    if 'current_warehouse' in request.session:
        current_warehouse_id = request.session['current_warehouse']['id']
        from store.models import Warehouse
        try:
            warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
            warehouse_prefix = f"{warehouse.name}_"
        except Warehouse.DoesNotExist:
            warehouse_prefix = f"{current_warehouse_id}_"
        invoices = Invoice.objects.filter(warehouse__warehouse_id=current_warehouse_id)
    else:
        invoices = Invoice.objects.all()

    columns = [
        'ID', 'Date', 'Customer Name', 'Contact Number', 'Item',
        'Warehouse', 'Price Per Item', 'Quantity', 'Shipping', 'Total', 'Grand Total'
    ]
    worksheet.append(columns)

    for invoice in invoices:
        if invoice.date.tzinfo is not None:
            date = invoice.date.replace(tzinfo=None)
        else:
            date = invoice.date

        warehouse_name = invoice.warehouse.name if invoice.warehouse else "N/A"

        worksheet.append([
            invoice.id,
            date,
            invoice.customer_name,
            invoice.contact_number,
            invoice.item.name,
            warehouse_name,
            invoice.price_per_item,
            invoice.quantity,
            invoice.shipping,
            invoice.total,
            invoice.grand_total
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = f'attachment; filename={warehouse_prefix}invoices_{timezone.now().strftime("%Y%m%d")}.xlsx'
    workbook.save(response)

    return response
