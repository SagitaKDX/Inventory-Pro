import json
import logging

from django.http import JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Sum, F, Q
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.utils import timezone
import csv
import io
from datetime import datetime, timedelta

from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

from openpyxl import Workbook

from accounts.models import Customer
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm, WarehouseDistributionForm
from store.models import Item, Warehouse, WarehouseInventory


logger = logging.getLogger(__name__)


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

# export sales and purchases to excel
def export_sales_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Sales'
    warehouse_prefix = ""
    if 'current_warehouse' in request.session:
        current_warehouse_id = request.session['current_warehouse']['id']
        warehouse_prefix = f"{current_warehouse_id}_"
        sales = Sale.objects.filter(warehouse__warehouse_id=current_warehouse_id)
    else:
        sales = Sale.objects.all()

    columns = [
        'ID', 'Date', 'Customer', 'Warehouse', 'Sub Total',
        'Grand Total', 'Tax Amount', 'Tax Percentage',
        'Amount Paid', 'Amount Change'
    ]
    worksheet.append(columns)

    for sale in sales:
        if sale.date_added.tzinfo is not None:
            date_added = sale.date_added.replace(tzinfo=None)
        else:
            date_added = sale.date_added

        warehouse_name = sale.warehouse.name if sale.warehouse else "N/A"

        worksheet.append([
            sale.id,
            date_added,
            sale.customer.phone,
            warehouse_name,
            sale.sub_total,
            sale.grand_total,
            sale.tax_amount,
            sale.tax_percentage,
            sale.amount_paid,
            sale.amount_change
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = f'attachment; filename={warehouse_prefix}sales.xlsx'
    workbook.save(response)

    return response


def export_purchases_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Purchases'

    warehouse_prefix = ""
    if 'current_warehouse' in request.session:
        current_warehouse_id = request.session['current_warehouse']['id']
        warehouse_prefix = f"{current_warehouse_id}_"
        
        purchases = Purchase.objects.filter(warehouse__warehouse_id=current_warehouse_id)
    else:
        purchases = Purchase.objects.all()

    columns = [
        'ID', 'Item', 'Warehouse', 'Description', 'Vendor', 'Order Date',
        'Delivery Date', 'Quantity', 'Delivery Status',
        'Price per item (VND)', 'Total Value'
    ]
    worksheet.append(columns)

    for purchase in purchases:
        delivery_tzinfo = purchase.delivery_date.tzinfo
        order_tzinfo = purchase.order_date.tzinfo

        if delivery_tzinfo or order_tzinfo is not None:
            delivery_date = purchase.delivery_date.replace(tzinfo=None)
            order_date = purchase.order_date.replace(tzinfo=None)
        else:
            delivery_date = purchase.delivery_date
            order_date = purchase.order_date
            
        warehouse_name = purchase.warehouse.name if purchase.warehouse else "N/A"
            
        worksheet.append([
            purchase.id,
            purchase.item.name,
            warehouse_name,
            purchase.description,
            purchase.vendor.name,
            order_date,
            delivery_date,
            purchase.quantity,
            purchase.get_delivery_status_display(),
            purchase.price,
            purchase.total_value
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = f'attachment; filename={warehouse_prefix}purchases.xlsx'
    workbook.save(response)

    return response

# list of sales
class SaleListView(LoginRequiredMixin, ListView):
   

    model = Sale
    template_name = "transactions/sales_list.html"
    context_object_name = "sales"
    paginate_by = 10
    ordering = ['date_added']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            queryset = queryset.filter(warehouse__warehouse_id=current_warehouse_id)
            
        return queryset

# sale detail view
class SaleDetailView(LoginRequiredMixin, DetailView):
 

    model = Sale
    template_name = "transactions/saledetail.html"

# sale create view
def SaleCreateView(request):
    if 'current_warehouse' not in request.session:
        messages.error(request, "Please select a warehouse before creating a sale.")
        return redirect('warehouse-list')
    
    current_warehouse_id = request.session['current_warehouse']['id']
    
    try:
        current_warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id, is_active=True)
    except Warehouse.DoesNotExist:
        messages.error(request, "Selected warehouse does not exist or is inactive.")
        return redirect('warehouse-list')
    warehouse_items = WarehouseInventory.objects.filter(
        warehouse=current_warehouse,
        is_active=True,
        quantity__gt=0
    ).select_related('item')
    
    context = {
        "active_icon": "sales",
        "customers": [c.to_select2() for c in Customer.objects.all()],
        "current_warehouse": current_warehouse,
        "warehouse_items": warehouse_items
    }

    if request.method == 'POST':
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)
                logger.info(f"Received data: {data}")

                required_fields = [
                    'customer', 'sub_total', 'grand_total',
                    'amount_paid', 'amount_change', 'items'
                ]
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")

                sale_attributes = {
                    "customer": Customer.objects.get(id=int(data['customer'])),
                    "warehouse": current_warehouse,
                    "sub_total": float(data["sub_total"]),
                    "grand_total": float(data["grand_total"]),
                    "tax_amount": float(data.get("tax_amount", 0.0)),
                    "tax_percentage": float(data.get("tax_percentage", 0.0)),
                    "amount_paid": float(data["amount_paid"]),
                    "amount_change": float(data["amount_change"]),
                }

                # Use a transaction to ensure atomicity
                with transaction.atomic():
                    new_sale = Sale.objects.create(**sale_attributes)
                    logger.info(f"Sale created: {new_sale}")

                    items = data["items"]
                    if not isinstance(items, list):
                        raise ValueError("Items should be a list")

                    for item in items:
                        if not all(
                            k in item for k in [
                                "id", "price", "quantity", "total_item"
                            ]
                        ):
                            raise ValueError("Item is missing required fields")

                        item_instance = Item.objects.get(id=int(item["id"]))
                        
                        try:
                            warehouse_inventory = WarehouseInventory.objects.get(
                                item=item_instance,
                                warehouse=current_warehouse,
                                is_active=True
                            )
                            
                            if warehouse_inventory.quantity < int(item["quantity"]):
                                raise ValueError(f"Not enough stock for item: {item_instance.name} in warehouse {current_warehouse.name}")
                            warehouse_inventory.quantity -= int(item["quantity"])
                            warehouse_inventory.save()
                            
                        except WarehouseInventory.DoesNotExist:
                            raise ValueError(f"Item {item_instance.name} is not available in warehouse {current_warehouse.name}")

                        detail_attributes = {
                            "sale": new_sale,
                            "item": item_instance,
                            "warehouse": current_warehouse,
                            "price": float(item["price"]),
                            "quantity": int(item["quantity"]),
                            "total_detail": float(item["total_item"])
                        }
                        SaleDetail.objects.create(**detail_attributes)
                        logger.info(f"Sale detail created: {detail_attributes}")

                        item_instance.quantity -= int(item["quantity"])
                        item_instance.save()

                return JsonResponse(
                    {
                        'status': 'success',
                        'message': 'Sale created successfully!',
                        'redirect': '/transactions/sales/'
                    }
                )

            except json.JSONDecodeError:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Invalid JSON format in request body!'
                    }, status=400)
            except Customer.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Customer does not exist!'
                    }, status=400)
            except Item.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Item does not exist!'
                    }, status=400)
            except ValueError as ve:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Value error: {str(ve)}'
                    }, status=400)
            except TypeError as te:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Type error: {str(te)}'
                    }, status=400)
            except Exception as e:
                logger.error(f"Exception during sale creation: {e}")
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': (
                            f'There was an error during the creation: {str(e)}'
                        )
                    }, status=500)

    return render(request, "transactions/sale_create.html", context=context)

# delete a sale
class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
   

    model = Sale
    template_name = "transactions/saledelete.html"

    def get_success_url(self):
        return reverse("saleslist")

    def test_func(self):
        return self.request.user.is_superuser

# list of purchases
class PurchaseListView(LoginRequiredMixin, ListView):

    model = Purchase
    template_name = "transactions/purchases_list.html"
    context_object_name = "purchases"
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            queryset = queryset.filter(warehouse__warehouse_id=current_warehouse_id)
        queryset = queryset.select_related('item', 'warehouse', 'vendor', 'item__category')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        logger.debug(f"Found {queryset.count()} purchases in the queryset")
        
        grouped_purchases = {}
        for purchase in queryset:
            item_id = purchase.item.id
            if item_id not in grouped_purchases:
                grouped_purchases[item_id] = {
                    'item_id': item_id,
                    'item_name': purchase.item.name,
                    'item_category': purchase.item.category.name if purchase.item.category else "Uncategorized",
                    'total_quantity': 0,
                    'total_value': 0,
                    'warehouses': [],
                    'latest_date': purchase.order_date,
                    'vendors': set()  
                }
            
            grouped_purchases[item_id]['total_quantity'] += purchase.quantity
            grouped_purchases[item_id]['total_value'] += purchase.total_value
        
            if purchase.vendor:
                grouped_purchases[item_id]['vendors'].add(purchase.vendor.name)

            if purchase.order_date > grouped_purchases[item_id]['latest_date']:
                grouped_purchases[item_id]['latest_date'] = purchase.order_date
            
            warehouse_name = purchase.warehouse.name if purchase.warehouse else "Unassigned"
            grouped_purchases[item_id]['warehouses'].append({
                'purchase_id': purchase.id,
                'warehouse': purchase.warehouse,
                'warehouse_name': warehouse_name,
                'quantity': purchase.quantity,
                'price': purchase.price,
                'total_value': purchase.total_value,
                'order_date': purchase.order_date,
                'delivery_date': purchase.delivery_date,
                'delivery_status': purchase.get_delivery_status_display(),
                'vendor': purchase.vendor,
                'vendor_name': purchase.vendor.name if purchase.vendor else "Unknown"
            })
        
        grouped_purchases_list = [
            {
                'item_id': data['item_id'],
                'item_name': data['item_name'],
                'item_category': data['item_category'],
                'total_quantity': data['total_quantity'],
                'total_value': data['total_value'],
                'latest_date': data['latest_date'],
                'vendors': ", ".join(data['vendors']) if data['vendors'] else "Unknown",
                'warehouses': sorted(data['warehouses'], key=lambda x: x['warehouse_name'] if x['warehouse'] else "")
            }
            for item_id, data in grouped_purchases.items()
        ]
        
        grouped_purchases_list.sort(key=lambda x: x['latest_date'], reverse=True)
        logger.debug(f"Grouped into {len(grouped_purchases_list)} unique items")
        
        context['grouped_purchases'] = grouped_purchases_list
        return context

# purchase detail
class PurchaseDetailView(LoginRequiredMixin, DetailView):

    model = Purchase
    template_name = "transactions/purchasedetail.html"

# create a purchase
class PurchaseCreateView(LoginRequiredMixin, CreateView):
   
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step = self.request.GET.get('step', '1')
        context['step'] = step
        context['warehouses'] = Warehouse.objects.filter(is_active=True).order_by('name')
        if 'purchase_form_data' in self.request.session:
            context['form_data'] = self.request.session['purchase_form_data']
        if 'warehouse_distribution' in self.request.session:
            context['warehouse_distribution'] = self.request.session['warehouse_distribution']
            
        if step == '2':
            context['distribution_form'] = WarehouseDistributionForm()
            
            total_distributed = 0
            total_quantity = 0
            
            if 'warehouse_distribution' in self.request.session:
                for dist in self.request.session['warehouse_distribution']:
                    try:
                        total_distributed += int(float(dist['quantity']))
                    except (ValueError, TypeError):
                        logger.error(f"Invalid quantity in distribution: {dist.get('quantity')}")
            
            if 'purchase_form_data' in self.request.session and 'quantity' in self.request.session['purchase_form_data']:
                try:
                    total_quantity = int(float(self.request.session['purchase_form_data']['quantity']))
                except (ValueError, TypeError):
                    total_quantity = 0
                    logger.error(f"Invalid quantity in form data: {self.request.session['purchase_form_data'].get('quantity')}")
            
            remaining_quantity = max(0, total_quantity - total_distributed)
            
            context['total_distributed'] = total_distributed
            context['total_quantity'] = total_quantity
            context['remaining_quantity'] = remaining_quantity
            context['is_fully_distributed'] = (total_distributed == total_quantity and total_quantity > 0)
            
            logger.debug(f"Context data for step 2: total_distributed={total_distributed}, total_quantity={total_quantity}, remaining={remaining_quantity}, is_fully_distributed={context['is_fully_distributed']}")
            
        return context
    
    def get(self, request, *args, **kwargs):
        step = request.GET.get('step', '1')
        if step == '1' and 'purchase_form_data' not in request.session:
            if 'purchase_form_data' in request.session:
                del request.session['purchase_form_data']
            if 'warehouse_distribution' in request.session:
                del request.session['warehouse_distribution']
            request.session.modified = True
            
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        step = request.POST.get('step', '1')
        
        logger.debug(f"Processing purchase form POST for step {step}")
        
        if step == '1':
            if form.is_valid():
                form_data = {
                    'item': form.cleaned_data['item'].pk,
                    'item_name': form.cleaned_data['item'].name,
                    'description': form.cleaned_data['description'],
                    'vendor': form.cleaned_data['vendor'].pk,
                    'vendor_name': form.cleaned_data['vendor'].name,
                    'quantity': str(form.cleaned_data['quantity']),
                    'price': str(form.cleaned_data['price']),
                    'delivery_date': form.cleaned_data['delivery_date'].strftime('%Y-%m-%d'),
                    'delivery_status': form.cleaned_data['delivery_status']
                }
                
                request.session['purchase_form_data'] = form_data
                request.session.modified = True
                
                logger.debug(f"Saved form data to session: {form_data}")
                
                return redirect(f"{reverse('purchase-create')}?step=2")
            else:
                logger.error(f"Form validation failed: {form.errors}")
                return self.form_invalid(form)
                
        elif step == '2':
            if 'save_purchase' in request.POST:
                try:
                    logger.debug("Processing save_purchase request")
                    
                    form_data = request.session.get('purchase_form_data')
                    if not form_data:
                        logger.error("No form data found in session")
                        messages.error(request, "No purchase data found. Please start again.")
                        return redirect('purchase-create')
                    
                    distribution = request.session.get('warehouse_distribution', [])
                    logger.debug(f"Distribution at save time: {distribution}")
                    
                    if not distribution:
                        logger.error("No warehouse distribution found")
                        messages.error(request, "No warehouse distribution found. Please add at least one warehouse.")
                        return redirect(f"{reverse('purchase-create')}?step=2")
                    
                    try:
                        total_distributed = sum(int(float(dist['quantity'])) for dist in distribution)
                        total_quantity = int(float(form_data['quantity']))
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error calculating quantities: {str(e)}")
                        messages.error(request, "Error calculating quantities. Please check your inputs.")
                        return redirect(f"{reverse('purchase-create')}?step=2")
                    
                    logger.debug(f"Total distributed: {total_distributed}, Total quantity: {total_quantity}")
                    
                    if total_distributed != total_quantity:
                        logger.warning(f"Distribution mismatch: {total_distributed} != {total_quantity}")
                        messages.warning(request, f"Distribution mismatch: {total_distributed} distributed out of {total_quantity} total. Please distribute all items.")
                        return redirect(f"{reverse('purchase-create')}?step=2")
                    created_purchases = []
                    
                    for dist in distribution:
                        try:
                            warehouse = Warehouse.objects.get(warehouse_id=dist['warehouse_id'])
                            item_id = form_data['item']
                            quantity = int(float(dist['quantity']))
                            purchase = Purchase(
                                item_id=item_id,
                                description=form_data['description'],
                                vendor_id=form_data['vendor'],
                                price=form_data['price'],
                                quantity=quantity,
                                delivery_date=form_data['delivery_date'],
                                delivery_status=form_data['delivery_status'],
                                warehouse=warehouse
                            )
                            purchase.total_value = float(form_data['price']) * quantity
                            purchase.save()
                            created_purchases.append(purchase)
                            logger.debug(f"Created purchase: {purchase.id} for warehouse {warehouse.name}")
                            
                        except Warehouse.DoesNotExist:
                            logger.error(f"Warehouse with ID {dist['warehouse_id']} not found")
                            messages.warning(request, f"Warehouse with ID {dist['warehouse_id']} not found. Skipping this distribution.")
                            continue
                        except Exception as e:
                            logger.error(f"Error creating purchase for warehouse {dist.get('warehouse_name')}: {str(e)}")
                            messages.warning(request, f"Error creating purchase for warehouse {dist.get('warehouse_name')}: {str(e)}")
                            continue
                    
                    if created_purchases:
                        if 'purchase_form_data' in self.request.session:
                            del request.session['purchase_form_data']
                        if 'warehouse_distribution' in self.request.session:
                            del request.session['warehouse_distribution']
                        request.session.modified = True
                        
                        messages.success(request, f"Successfully created {len(created_purchases)} purchase orders.")
                        return redirect('purchaseslist')
                    else:
                        messages.error(request, "No purchases were created. Please check the logs for details.")
                        return redirect(f"{reverse('purchase-create')}?step=2")
                    
                except Exception as e:
                    logger.error(f"Error saving purchase: {str(e)}")
                    messages.error(request, f"Error saving purchase: {str(e)}")
                    return redirect(f"{reverse('purchase-create')}?step=2")
            
            warehouse_id = request.POST.get('warehouse')
            quantity = request.POST.get('quantity')
            
            logger.debug(f"Processing warehouse distribution: warehouse_id={warehouse_id}, quantity={quantity}")
            
            try:
                total_quantity = int(float(request.session.get('purchase_form_data', {}).get('quantity', 0)))
                logger.debug(f"Total quantity from session: {total_quantity}")
            except (ValueError, TypeError):
                total_quantity = 0
                logger.error(f"Error parsing total quantity from session: {request.session.get('purchase_form_data', {}).get('quantity')}")
            
            if warehouse_id and quantity:
                try:
                    warehouse = Warehouse.objects.get(warehouse_id=warehouse_id)
                    quantity = int(float(quantity))
                    distribution = request.session.get('warehouse_distribution', [])
                    logger.debug(f"Current distribution: {distribution}")
                    current_total = sum(int(float(dist['quantity'])) for dist in distribution)
                    logger.debug(f"Current total distributed: {current_total}")
                    if current_total + quantity > total_quantity:
                        logger.debug(f"Adjusting quantity from {quantity} to {max(0, total_quantity - current_total)} to prevent exceeding total")
                        quantity = max(0, total_quantity - current_total)
                        
                    if quantity > 0:
                        exists = False
                        for i, dist in enumerate(distribution):
                            if dist['warehouse_id'] == warehouse_id:
                                old_quantity = distribution[i]['quantity']
                                distribution[i]['quantity'] = int(float(distribution[i]['quantity'])) + quantity
                                logger.debug(f"Updated existing warehouse {warehouse.name} quantity from {old_quantity} to {distribution[i]['quantity']}")
                                exists = True
                                break
                                
                        if not exists:
                            distribution.append({
                                'warehouse_id': warehouse_id,
                                'warehouse_name': warehouse.name,
                                'quantity': quantity
                            })
                            logger.debug(f"Added new warehouse {warehouse.name} with quantity {quantity}")
                        request.session['warehouse_distribution'] = distribution
                        request.session.modified = True
                        new_total = sum(int(float(dist['quantity'])) for dist in distribution)
                        logger.debug(f"Updated distribution: {distribution}")
                        logger.debug(f"New total distributed: {new_total}/{total_quantity}")
                    
                except (Warehouse.DoesNotExist, ValueError) as e:
                    logger.error(f"Error processing warehouse quantity: {str(e)}")
            
            if 'remove_warehouse' in request.POST:
                warehouse_id = request.POST.get('remove_warehouse')
                logger.debug(f"Removing warehouse from distribution: warehouse_id={warehouse_id}")
                
                distribution = request.session.get('warehouse_distribution', [])
                old_total = sum(int(float(dist['quantity'])) for dist in distribution)
                
                request.session['warehouse_distribution'] = [
                    dist for dist in distribution if dist['warehouse_id'] != warehouse_id
                ]
                request.session.modified = True
                
                new_distribution = request.session['warehouse_distribution']
                new_total = sum(int(float(dist['quantity'])) for dist in new_distribution)
                logger.debug(f"Updated distribution after removal: {new_distribution}")
                logger.debug(f"New total after removal: {new_total}/{total_quantity} (was {old_total})")
            
            return redirect(f"{reverse('purchase-create')}?step=2")
        
        return self.get(request, *args, **kwargs)

# update a purchase
class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
   

    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.object.warehouse and 'current_warehouse' in self.request.session:
            current_warehouse_id = self.request.session['current_warehouse']['id']
            try:
                warehouse = Warehouse.objects.get(warehouse_id=current_warehouse_id)
                form.fields['warehouse'].initial = warehouse
            except Warehouse.DoesNotExist:
                pass
        return form
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Purchase updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('purchaseslist')

# delete a purchase
class PurchaseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):

    model = Purchase
    template_name = "transactions/purchasedelete.html"

    def delete(self, request, *args, **kwargs):
        purchase = self.get_object()
        
        purchase.item.quantity -= purchase.quantity
        purchase.item.save()
        if purchase.warehouse:
            try:
                inventory = WarehouseInventory.objects.get(
                    item=purchase.item,
                    warehouse=purchase.warehouse
                )
                inventory.quantity -= purchase.quantity
                
                if inventory.quantity <= 0:
                    inventory.quantity = 0
                    inventory.is_active = False
                
                inventory.save()
            except WarehouseInventory.DoesNotExist:
                pass  
        
        messages.success(request, f"Purchase deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("purchaseslist")

    def test_func(self):
        return self.request.user.is_superuser
