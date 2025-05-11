from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook

from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView
)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

from django_tables2 import SingleTableView
from django_tables2.export.views import ExportMixin

from .models import Bill
from .tables import BillTable
from accounts.models import Profile

# displaying list of bills
class BillListView(LoginRequiredMixin, ExportMixin, SingleTableView):
    model = Bill
    table_class = BillTable
    template_name = 'bills/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 10
    SingleTableView.table_pagination = False
    
    def get_queryset(self):
        queryset = super().get_queryset()
        view_mode = self.request.GET.get('view_mode', 'all')
        self.view_mode = view_mode
        
        if view_mode == 'current' and 'current_warehouse' in self.request.session:
            # Filter bills by current warehouse
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

# creat new bill
class BillCreateView(LoginRequiredMixin, CreateView):
    model = Bill
    template_name = 'bills/billcreate.html'
    fields = [
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
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
        return reverse('bill_list')

# update an existing bill
class BillUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Bill
    template_name = 'bills/billupdate.html'
    fields = [
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
    ]

    def form_valid(self, form):
        # Automatically set the warehouse to the current warehouse, for saved bills.
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            from store.models import Warehouse
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.instance.warehouse = warehouse
            except Warehouse.DoesNotExist:
                pass
        return super().form_valid(form)

    def test_func(self):
        return self.request.user.profile in Profile.objects.all()

    def get_success_url(self):
        return reverse('bill_list')

# delete a bill
class BillDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Bill
    template_name = 'bills/billdelete.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_success_url(self):
        return reverse('bill_list')

@login_required
def export_bills_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Bills'
    warehouse_prefix = ""
    if 'current_warehouse' in request.session:
        current_warehouse_id = request.session['current_warehouse']['id']
        from store.models import Warehouse
        try:
            warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
            warehouse_prefix = f"{warehouse.name}_"
        except Warehouse.DoesNotExist:
            warehouse_prefix = f"{current_warehouse_id}_"
        bills = Bill.objects.filter(warehouse__warehouse_id=current_warehouse_id)
    else:
        bills = Bill.objects.all()

    columns = [
        'ID', 'Date', 'Institution Name', 'Warehouse', 'Phone Number', 'Email',
        'Address', 'Description', 'Payment Details', 'Amount', 'Status'
    ]
    worksheet.append(columns)

    for bill in bills:
        if bill.date.tzinfo is not None:
            date = bill.date.replace(tzinfo=None)
        else:
            date = bill.date

        warehouse_name = bill.warehouse.name if bill.warehouse else "N/A"
        status = "Paid" if bill.status else "Unpaid"

        worksheet.append([
            bill.id,
            date,
            bill.institution_name,
            warehouse_name,
            bill.phone_number,
            bill.email,
            bill.address,
            bill.description,
            bill.payment_details,
            bill.amount,
            status
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = f'attachment; filename={warehouse_prefix}bills_{timezone.now().strftime("%Y%m%d")}.xlsx'
    workbook.save(response)

    return response
