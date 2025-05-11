from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    InvoiceListView,
    InvoiceDetailView,
    InvoiceCreateView,
    InvoiceUpdateView,
    InvoiceDeleteView,
    export_invoices_to_excel
)

urlpatterns = [
    # Invoice URLs
    path(
        'invoices/',
        InvoiceListView.as_view(),
        name='invoicelist'
    ),
    path(
        'invoice/<slug:slug>/',
        InvoiceDetailView.as_view(),
        name='invoice-detail'
    ),
    path(
        'new-invoice/',
        InvoiceCreateView.as_view(),
        name='invoice-create'
    ),
    path(
        'invoice/<slug:slug>/update/',
        InvoiceUpdateView.as_view(),
        name='invoice-update'
    ),
    path(
        'invoice/<int:pk>/delete/',
        InvoiceDeleteView.as_view(),
        name='invoice-delete'
    ),
    path('export/', export_invoices_to_excel, name='invoices-export'),
]

# Static media files configuration for development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
