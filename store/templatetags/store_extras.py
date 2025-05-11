from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def sum_quantity(distribution_list):
    if not distribution_list:
        return 0
    if isinstance(distribution_list, int):
        return distribution_list
    try:
        return sum(int(dist.get('quantity', 0)) for dist in distribution_list)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    try:
        value_int = int(float(value))
        
        if isinstance(arg, list):
            arg_sum = sum(int(float(dist.get('quantity', 0))) for dist in arg)
            result = value_int - arg_sum
            return result if result >= 0 else 0
        else:
            arg_int = int(float(arg))
            result = value_int - arg_int
            return result if result >= 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def dict_lookup(choices, key):
    for choice_key, choice_value in choices:
        if str(choice_key) == str(key):
            return choice_value
    return ""

@register.filter
def is_warehouse_used(distribution_list, warehouse_id):
    if not distribution_list:
        return False
    
    for dist in distribution_list:
        if str(dist.get('warehouse_id', '')) == str(warehouse_id):
            return True
    return False 