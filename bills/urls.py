from django.urls import path

from .views import (
    BillListView,
    BillCreateView,
    BillUpdateView,
    BillDeleteView,
    export_bills_to_excel
)

urlpatterns = [
    path('', BillListView.as_view(), name='bill_list'),
    path('create/', BillCreateView.as_view(), name='bill-create'),
    path(
        '<slug:slug>/update/',
        BillUpdateView.as_view(),
        name='bill-update'
    ),
    path(
        '<slug:slug>/delete/',
        BillDeleteView.as_view(),
        name='bill-delete'
    ),
    path('export/', export_bills_to_excel, name='bills-export'),
]
