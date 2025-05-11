from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages

class WarehouseMiddleware:
    """
    Middleware to ensure a warehouse is selected for certain views.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.warehouse_required_views = [
            'purchase-create',
            'sale-create',
            'delivery-create',
        ]
        self.exempt_views = [
            'warehouse-list',
            'warehouse-create',
            'warehouse-detail',
            'warehouse-update',
            'set-current-warehouse',
            'user-login',
            'logout',
            'admin:index',
        ]

    def __call__(self, request):
        # Skip middleware for admin and login pages
        if request.path.startswith('/admin/') or not request.user.is_authenticated:
            return self.get_response(request)
        # Get current URL name
        current_url_name = resolve(request.path_info).url_name
        if (current_url_name in self.warehouse_required_views and 
            'current_warehouse' not in request.session and
            current_url_name not in self.exempt_views):
            
            messages.warning(request, 'Please select a warehouse to continue.')
            return redirect(reverse('warehouse-list'))
            
        response = self.get_response(request)
        return response 