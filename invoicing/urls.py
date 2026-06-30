from django.urls import path

from . import views

urlpatterns = [
    # Factures OR
    path("", views.InvoiceListView.as_view(), name="invoice_list"),
    path("<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("<int:pk>/imprimer/", views.InvoicePrintView.as_view(), name="invoice_print"),
    path("<int:pk>/recu/<int:payment_pk>/", views.PaymentReceiptView.as_view(), name="payment_receipt"),
    path("<int:pk>/paiement/", views.AddPaymentView.as_view(), name="payment_add"),

    # Proformas (workflow autonome)
    path("proforma/", views.ProformaListView.as_view(), name="proforma_list"),
    path("proforma/nouveau/", views.ProformaCreateView.as_view(), name="proforma_create"),
    path("proforma/<int:pk>/", views.ProformaDetailView.as_view(), name="proforma_detail"),
    path("proforma/<int:pk>/modifier/", views.ProformaEditView.as_view(), name="proforma_edit"),
    path("proforma/<int:pk>/avancer/", views.ProformaPromoteView.as_view(), name="proforma_promote"),
    path("proforma/<int:pk>/imprimer/", views.ProformaPrintView.as_view(), name="proforma_print"),
]
