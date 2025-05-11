from .models import Warehouse

def warehouse_context(request):
    context = {
        'warehouses': Warehouse.objects.filter(is_active=True).order_by('name'),
    }
    
    if 'current_warehouse' in request.session:
        context['current_warehouse'] = request.session['current_warehouse']
    
    return context 