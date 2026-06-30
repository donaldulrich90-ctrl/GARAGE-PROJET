from django.urls import path

from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:pk>/imprimer/', views.InvoicePrintView.as_view(), name='invoice_print'),
    path('<int:pk>/recu/<int:payment_pk>/', views.PaymentReceiptView.as_view(), name='payment_receipt'),
    path('<int:pk>/paiement/', views.AddPaymentView.as_view(), name='payment_add'),
]
