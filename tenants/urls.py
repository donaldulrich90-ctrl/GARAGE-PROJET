from django.urls import path

from . import views

urlpatterns = [
    path("", views.garage_list, name="garage_list"),
    path("nouveau/", views.garage_create, name="garage_create"),
    path("<int:pk>/modifier/", views.garage_edit, name="garage_edit"),
    path("<int:pk>/toggle/", views.garage_toggle, name="garage_toggle"),
    path("<int:pk>/fournisseur/", views.garage_supplier_create, name="garage_supplier_create"),
    # Fournisseurs indépendants (back-office plateforme)
    path("fournisseurs/", views.platform_supplier_list, name="platform_supplier_list"),
    path("fournisseurs/nouveau/", views.platform_supplier_create, name="platform_supplier_create"),
]
