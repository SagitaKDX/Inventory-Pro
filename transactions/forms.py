from django import forms
from .models import Purchase
from store.models import Warehouse


class BootstrapMixin(forms.ModelForm):
  
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class PurchaseForm(BootstrapMixin, forms.ModelForm):
    
    class Meta:
        model = Purchase
        fields = [
            'item', 'price', 'description', 'vendor',
            'quantity', 'delivery_date', 'delivery_status'
        ]
        widgets = {
            'delivery_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'description': forms.Textarea(
                attrs={'rows': 1, 'cols': 40}
            ),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),
            'delivery_status': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'price': forms.NumberInput(
                attrs={'class': 'form-control'}
            ),
        }


class WarehouseDistributionForm(forms.Form):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Warehouse"
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
