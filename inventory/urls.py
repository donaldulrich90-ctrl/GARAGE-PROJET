from django.urls import path

from . import views

urlpatterns = [
    path('', views.PartListView.as_view(), name='part_list'),
    path('pieces/nouveau/', views.PartCreateView.as_view(), name='part_create'),
    path('pieces/<int:pk>/modifier/', views.PartUpdateView.as_view(), name='part_update'),
    path('fournisseurs/', views.SupplierListView.as_view(), name='supplier_list'),
    path('fournisseurs/nouveau/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('fournisseurs/<int:pk>/modifier/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    # Offres fournisseurs (SupplierPart) — vue en lecture seule côté garage.
    # La création/édition/suppression est reservee au portail fournisseur
    # (/fournisseur/mes-pieces/) — cf. app supplier_portal.
    path('offres/', views.SupplierPartListView.as_view(), name='supplier_part_list'),
    path('catalogue/rechercher/', views.PartSearchView.as_view(), name='part_search'),
    path('catalogue/piece/<int:pk>/comparer/', views.CatalogPartCompareView.as_view(), name='catalog_part_compare'),
    # Commandes fournisseur (côté garage)
    path('commandes/', views.SupplierOrderListView.as_view(), name='supplier_order_list'),
    path('commandes/<int:pk>/', views.SupplierOrderDetailView.as_view(), name='supplier_order_detail'),
    path('commandes/<int:pk>/soumettre/', views.SupplierOrderSubmitView.as_view(), name='supplier_order_submit'),
    path('commandes/<int:pk>/annuler/', views.SupplierOrderCancelView.as_view(), name='supplier_order_cancel'),
    path('commandes/<int:pk>/livrer/', views.SupplierOrderDeliverView.as_view(), name='supplier_order_deliver'),
    path('fournisseurs/<int:pk>/catalogue/', views.SupplierCatalogView.as_view(), name='supplier_catalog'),
    path('offres/<int:pk>/ajouter/', views.SupplierOrderAddLineView.as_view(), name='supplier_order_add_line'),
]
