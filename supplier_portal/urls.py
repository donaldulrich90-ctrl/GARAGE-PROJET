from django.urls import path

from . import views

app_name = "supplier_portal"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("mes-pieces/", views.MyOffersListView.as_view(), name="offer_list"),
    path("mes-pieces/nouveau/", views.MyOfferCreateView.as_view(), name="offer_create"),
    path("mes-pieces/<int:pk>/modifier/", views.MyOfferUpdateView.as_view(), name="offer_update"),
    path("mes-pieces/<int:pk>/supprimer/", views.MyOfferDeleteView.as_view(), name="offer_delete"),
    path("mouvements/", views.MovementListView.as_view(), name="movement_list"),
    path("mouvements/nouveau/", views.MovementCreateView.as_view(), name="movement_create"),
    path("ventes/", views.SalesListView.as_view(), name="sale_list"),
    path("depenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("depenses/nouveau/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("depenses/<int:pk>/modifier/", views.ExpenseUpdateView.as_view(), name="expense_update"),
    path("depenses/<int:pk>/supprimer/", views.ExpenseDeleteView.as_view(), name="expense_delete"),
    path("rapports/", views.ReportView.as_view(), name="report"),
    path("rapports/export-csv/", views.report_export_csv, name="report_export_csv"),
    path("profil/", views.ProfileView.as_view(), name="profile"),
    # Commandes reçues
    path("commandes/", views.OrderInboxView.as_view(), name="order_list"),
    path("commandes/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("commandes/<int:pk>/valider/", views.order_validate, name="order_validate"),
    path("commandes/<int:pk>/rejeter/", views.order_reject, name="order_reject"),
    path("commandes/<int:pk>/expedier/", views.order_ship, name="order_ship"),
    # Factures fournisseur
    path("factures/", views.invoice_list, name="invoice_list"),
    path("factures/nouvelle/", views.invoice_create, name="invoice_create"),
    path("factures/depuis-commande/<int:order_pk>/", views.invoice_from_order, name="invoice_from_order"),
    path("factures/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("factures/<int:pk>/ligne/ajouter/", views.invoice_add_line, name="invoice_add_line"),
    path("factures/<int:pk>/ligne/<int:line_pk>/supprimer/", views.invoice_line_delete, name="invoice_line_delete"),
    path("factures/<int:pk>/statut/<str:status>/", views.invoice_set_status, name="invoice_set_status"),
    path("factures/<int:pk>/supprimer/", views.invoice_delete, name="invoice_delete"),
]
