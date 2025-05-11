import operator
from functools import reduce
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    DetailView, CreateView, UpdateView, DeleteView, ListView
)
from django.views.generic.edit import FormMixin
from django.contrib import messages

from django_tables2 import SingleTableView, RequestConfig
import django_tables2 as tables
from django_tables2.export.views import ExportMixin

from accounts.models import Profile, Vendor
from transactions.models import Sale
from .models import Category, Item, Delivery, Warehouse, WarehouseInventory
from .forms import ItemForm, CategoryForm, DeliveryForm
from .tables import ItemTable


@login_required
def dashboard(request):
    profiles = Profile.objects.all()
    items = Item.objects.all()
    total_items = items.count()
    profiles_count = profiles.count()
    delivery = Delivery.objects.filter(is_delivered=False)
    sales = Sale.objects.all()

    # Prepare data for charts
    category_counts = Category.objects.annotate(
        item_count=Count("item")
    ).values("name", "item_count")
    categories = [cat["name"] for cat in category_counts]
    category_counts = [cat["item_count"] for cat in category_counts]

    sale_dates = (
        Sale.objects.values("date_added__date")
        .annotate(total_sales=Sum("grand_total"))
        .order_by("date_added__date")
    )
    sale_dates_labels = [
        date["date_added__date"].strftime("%Y-%m-%d") for date in sale_dates
    ]
    sale_dates_values = [float(date["total_sales"]) for date in sale_dates]

    warehouse_stats = {}
    if 'current_warehouse' in request.session:
        current_warehouse_id = request.session['current_warehouse']['id']
        try:
            warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
            warehouse_inventories = WarehouseInventory.objects.filter(
                warehouse=warehouse,
                is_active=True
            )
            
            warehouse_items_count = warehouse_inventories.count()
            low_stock_count = warehouse_inventories.filter(
                quantity__lt=F('min_stock_level'),
                quantity__gt=0
            ).count()
            out_of_stock_count = warehouse_inventories.filter(quantity=0).count()
            warehouse_stats = {
                'warehouse_items_count': warehouse_items_count,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
            }
        except Warehouse.DoesNotExist:
            if 'current_warehouse' in request.session:
                del request.session['current_warehouse']

    context = {
        'items': items,
        'profiles': profiles,
        'profiles_count': profiles_count,
        'total_items': total_items,
        'vendors': Vendor.objects.all(),
        'delivery': delivery,
        'sales': sales,
        'categories': categories,
        'category_counts': category_counts,
        'sale_dates_labels': sale_dates_labels,
        'sale_dates_values': sale_dates_values,
        **warehouse_stats
    }
    
    return render(request, 'store/dashboard.html', context)


class ProductListView(LoginRequiredMixin, ExportMixin, tables.SingleTableView):
    

    model = Item
    table_class = ItemTable
    template_name = "store/productslist.html"
    context_object_name = "items"
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        view_mode = self.request.GET.get('view_mode', 'all')
        self.view_mode = view_mode
        
        if view_mode == 'current' and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                warehouse_items = WarehouseInventory.objects.filter(
                    warehouse=warehouse,
                    is_active=True
                ).values_list('item_id', flat=True)
                queryset = queryset.filter(id__in=warehouse_items)
            except Warehouse.DoesNotExist:
                pass
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_mode'] = getattr(self, 'view_mode', 'all')
        if context['view_mode'] == 'current' and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                inventory_map = {
                    inv.item_id: inv.quantity 
                    for inv in WarehouseInventory.objects.filter(
                        warehouse=warehouse,
                        is_active=True
                    )
                }
                context['inventory_map'] = inventory_map
                context['current_warehouse'] = warehouse
            except Warehouse.DoesNotExist:
                pass
                
        return context


class ItemSearchListView(ProductListView):
    

    paginate_by = 10

    def get_queryset(self):
        result = super(ItemSearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.and_, (Q(name__icontains=q) for q in query_list)
                )
            )
        return result


class ProductDetailView(LoginRequiredMixin, FormMixin, DetailView):
    

    model = Item
    template_name = "store/productdetail.html"

    def get_success_url(self):
        return reverse("product-detail", kwargs={"slug": self.object.slug})


class ProductCreateView(LoginRequiredMixin, CreateView):
   
    model = Item
    template_name = "store/productcreate.html"
    form_class = ItemForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouses'] = Warehouse.objects.filter(is_active=True).order_by('name')
        
        context['form_data'] = {}
        context['warehouse_distribution'] = []
        if 'form' not in context:
            context['form'] = self.get_form()
        if 'product_form_data' in self.request.session:
            context['form_data'] = self.request.session['product_form_data']
            print("Form data found in session:", self.request.session['product_form_data'])
        
        if 'warehouse_distribution' in self.request.session:
            context['warehouse_distribution'] = self.request.session['warehouse_distribution']
            print("Warehouse distribution found in session:", self.request.session['warehouse_distribution'])
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        print("POST request received with data:", request.POST)
        step = request.POST.get('step', '1')
        print(f"Processing step {step}")
        
        if step == '1':
            print("Processing step 1 - Product Details")
            product_data = {
                'name': form.data.get('name', ''),
                'description': form.data.get('description', ''),
                'category': form.data.get('category', ''),
                'price': form.data.get('price', ''),
                'quantity': form.data.get('quantity', ''),
                'expiring_date': form.data.get('expiring_date', ''),
                'vendor': form.data.get('vendor', ''),
            }
            print("Saving initial form data to session:", product_data)
            request.session['product_form_data'] = product_data
            request.session.modified = True
            
            if form.is_valid():
                print("Form is valid, proceeding to step 2")
                return redirect(f"{reverse('product-create')}?step=2")
            else:
                print("Form is invalid, staying on step 1")
                return self.form_invalid(form)
                
        elif step == '2':
            print("Processing step 2 - Warehouse Distribution")
            if 'save_product' in request.POST:
                print("Save product button clicked")
                try:
                    form_data = request.session.get('product_form_data')
                    if not form_data:
                        messages.error(request, "Product data not found in session")
                        return redirect('product-create')
                    
                    distribution = request.session.get('warehouse_distribution', [])
                    total_distributed = sum(int(float(dist['quantity'])) for dist in distribution)
                    total_quantity = int(float(form_data['quantity']))
                    
                    if total_distributed != total_quantity:
                        messages.error(request, f"Total distributed quantity ({total_distributed}) does not match product quantity ({total_quantity})")
                        return redirect(f"{reverse('product-create')}?step=2")
                    product = Item.objects.create(
                        name=form_data['name'],
                        description=form_data['description'],
                        category_id=form_data['category'],
                        price=form_data['price'],
                        quantity=total_quantity,
                        expiring_date=form_data['expiring_date'],
                        vendor_id=form_data['vendor']
                    )
                    for dist in distribution:
                        warehouse = Warehouse.objects.get(warehouse_id=dist['warehouse_id'])
                        WarehouseInventory.objects.create(
                            warehouse=warehouse,
                            item=product,
                            quantity=int(float(dist['quantity'])),
                            is_active=True
                        )
                    if 'product_form_data' in request.session:
                        del request.session['product_form_data']
                    if 'warehouse_distribution' in request.session:
                        del request.session['warehouse_distribution']
                    request.session.modified = True
                    
                    messages.success(request, "Product created successfully!")
                    return redirect('productslist')
                    
                except Exception as e:
                    print(f"Error saving product: {str(e)}")
                    messages.error(request, f"Error creating product: {str(e)}")
                    return redirect(f"{reverse('product-create')}?step=2")
            
            warehouse_id = request.POST.get('warehouse')
            quantity = request.POST.get('quantity')
            total_quantity = int(float(request.session.get('product_form_data', {}).get('quantity', 0)))
            
            if warehouse_id and quantity:
                try:
                    warehouse = Warehouse.objects.get(warehouse_id=warehouse_id)
                    quantity = int(float(quantity))
                    print(f"Adding quantity {quantity} to warehouse {warehouse.name}")
                    
                    distribution = request.session.get('warehouse_distribution', [])
                    
                    for i, dist in enumerate(distribution):
                        if dist['warehouse_id'] == warehouse_id:
                            distribution[i]['quantity'] += quantity
                            break
                    else:
                        distribution.append({
                            'warehouse_id': warehouse_id,
                            'warehouse_name': warehouse.name,
                            'quantity': quantity
                        })
                    
                    request.session['warehouse_distribution'] = distribution
                    request.session.modified = True
                    print("Updated warehouse distribution:", distribution)
                    
                    distributed_quantity = sum(int(float(dist['quantity'])) for dist in distribution)
                    print(f"Total distributed: {distributed_quantity}, Total needed: {total_quantity}")
                    
                    if distributed_quantity > total_quantity:
                        messages.error(request, f"Total distributed quantity ({distributed_quantity}) exceeds product quantity ({total_quantity})")
                    elif distributed_quantity == total_quantity:
                        messages.success(request, "All quantities have been distributed. You can now save the product.")
                    else:
                        remaining = total_quantity - distributed_quantity
                        messages.info(request, f"Remaining quantity to distribute: {remaining}")
                except (Warehouse.DoesNotExist, ValueError) as e:
                    print(f"Error processing warehouse quantity: {str(e)}")
                    messages.error(request, "Invalid warehouse or quantity")
            
            if 'remove_warehouse' in request.POST:
                warehouse_id = request.POST.get('remove_warehouse')
                distribution = request.session.get('warehouse_distribution', [])
                print(f"Removing warehouse {warehouse_id} from distribution")
                request.session['warehouse_distribution'] = [
                    dist for dist in distribution if dist['warehouse_id'] != warehouse_id
                ]
                request.session.modified = True
                messages.info(request, "Warehouse distribution updated")
            
            return redirect(f"{reverse('product-create')}?step=2")
        
        return self.get(request, *args, **kwargs)


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    
    model = Item
    template_name = "store/productupdate.html"
    form_class = ItemForm
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
   

    model = Item
    template_name = "store/productdelete.html"
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class DeliveryListView(
    LoginRequiredMixin, ExportMixin, tables.SingleTableView
):
   

    model = Delivery
    pagination = 10
    template_name = "store/deliveries.html"
    context_object_name = "deliveries"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        view_mode = self.request.GET.get('view_mode', 'all')
        self.view_mode = view_mode
        
        if view_mode == 'current' and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
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
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                context['current_warehouse'] = warehouse
            except Warehouse.DoesNotExist:
                pass
                
        return context


class DeliverySearchListView(DeliveryListView):
  
    paginate_by = 10

    def get_queryset(self):
        result = super(DeliverySearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.
                    and_, (Q(customer_name__icontains=q) for q in query_list)
                )
            )
        return result


class DeliveryDetailView(LoginRequiredMixin, DetailView):
   
    model = Delivery
    template_name = "store/deliverydetail.html"


class DeliveryCreateView(LoginRequiredMixin, CreateView):
  
    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"
    
    def get_initial(self):
        initial = super().get_initial()
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                initial['warehouse'] = warehouse
            except Warehouse.DoesNotExist:
                pass
        return initial
    
    def form_valid(self, form):
        if not form.instance.warehouse and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.instance.warehouse = warehouse
            except Warehouse.DoesNotExist:
                pass
        return super().form_valid(form)


class DeliveryUpdateView(LoginRequiredMixin, UpdateView):
    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"
    
    def form_valid(self, form):
        if not form.instance.warehouse and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.instance.warehouse = warehouse
            except Warehouse.DoesNotExist:
                pass
        return super().form_valid(form)


class DeliveryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
 

    model = Delivery
    template_name = "store/productdelete.html"
    success_url = "/deliveries"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'store/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10
    login_url = 'login'


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'store/category_detail.html'
    context_object_name = 'category'
    login_url = 'login'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'store/category_confirm_delete.html'
    context_object_name = 'category'
    success_url = reverse_lazy('category-list')
    login_url = 'login'


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


@csrf_exempt
@require_POST
@login_required
def get_items_ajax_view(request):
    if is_ajax(request):
        try:
            term = request.POST.get("term", "")
            warehouse_id = request.POST.get("warehouse_id", None)
            data = []

            items_query = Item.objects.filter(name__icontains=term)
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(warehouse_id=warehouse_id)
                    warehouse_items = WarehouseInventory.objects.filter(
                        warehouse=warehouse,
                        is_active=True,
                        quantity__gt=0
                    ).values_list('item_id', flat=True)
                    
                    items_query = items_query.filter(id__in=warehouse_items)
                    
                    # For each item, include its available quantity in the warehouse
                    for item in items_query[:10]:
                        item_data = item.to_json()
                        try:
                            inventory = WarehouseInventory.objects.get(
                                item=item,
                                warehouse=warehouse,
                                is_active=True
                            )
                            item_data['available'] = inventory.quantity
                        except WarehouseInventory.DoesNotExist:
                            item_data['available'] = 0
                        
                        data.append(item_data)
                except Warehouse.DoesNotExist:
                    return JsonResponse(data, safe=False)
            else:
                for item in items_query[:10]:
                    data.append(item.to_json())

            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Not an AJAX request'}, status=400)


class WarehouseListView(LoginRequiredMixin, ListView):
    model = Warehouse
    template_name = 'store/warehouse_list.html'
    context_object_name = 'warehouses'
    
    def get_queryset(self):
        return Warehouse.objects.filter(is_active=True).order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_warehouse'] = self.request.session.get('current_warehouse', None)
        return context

class WarehouseCreateView(LoginRequiredMixin, CreateView):
    model = Warehouse
    template_name = 'store/warehouse_form.html'
    fields = ['warehouse_id', 'name', 'description']
    success_url = reverse_lazy('warehouse-list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Warehouse {form.instance.name} has been created!')
        return super().form_valid(form)

class WarehouseUpdateView(LoginRequiredMixin, UpdateView):
    model = Warehouse
    template_name = 'store/warehouse_form.html'
    fields = ['name', 'description', 'is_active']
    success_url = reverse_lazy('warehouse-list')
    
    def get_object(self):
        return get_object_or_404(Warehouse, warehouse_id=self.kwargs['pk'])
    
    def form_valid(self, form):
        messages.success(self.request, f'Warehouse {form.instance.name} has been updated!')
        return super().form_valid(form)

class WarehouseDetailView(LoginRequiredMixin, DetailView):
    model = Warehouse
    template_name = 'store/warehouse_detail.html'
    
    def get_object(self):
        return get_object_or_404(Warehouse, warehouse_id=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.get_object()
        context['inventory_items'] = WarehouseInventory.objects.filter(
            warehouse=warehouse, 
            is_active=True
        ).select_related('item')
        return context

@login_required
def set_current_warehouse(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, warehouse_id=warehouse_id, is_active=True)
    request.session['current_warehouse'] = {
        'id': warehouse.warehouse_id,
        'name': warehouse.name
    }
    messages.success(request, f'Current warehouse set to: {warehouse.name}')
    next_url = request.GET.get('next', reverse('warehouse-list'))
    return redirect(next_url)

@login_required
def manage_inventory(request, item_id, warehouse_id):

    item = get_object_or_404(Item, id=item_id)
    warehouse = get_object_or_404(Warehouse, warehouse_id=warehouse_id, is_active=True)
    inventory, created = WarehouseInventory.objects.get_or_create(
        item=item,
        warehouse=warehouse,
        defaults={
            'quantity': 0,
            'min_stock_level': 5,
            'max_stock_level': 100,
            'is_active': True
        }
    )
    
    if request.method == 'POST':
        quantity = request.POST.get('quantity', 0)
        location_code = request.POST.get('location_code', '')
        min_stock_level = request.POST.get('min_stock_level', 5)
        max_stock_level = request.POST.get('max_stock_level', 100)
        
        try:
            inventory.quantity = int(quantity)
            inventory.location_code = location_code
            inventory.min_stock_level = int(min_stock_level)
            inventory.max_stock_level = int(max_stock_level)
            if inventory.quantity <= 0:
                inventory.quantity = 0
                inventory.is_active = False
            else:
                inventory.is_active = True
                
            inventory.save()
            
            messages.success(request, f'Inventory updated for {item.name} in {warehouse.name}')
            return redirect(f"{reverse('productslist')}?view_mode=current")
            
        except ValueError:
            messages.error(request, 'Please enter valid numbers for quantity and stock levels')
    
    context = {
        'item': item,
        'warehouse': warehouse,
        'inventory': inventory,
    }
    
    return render(request, 'store/manage_inventory.html', context)
