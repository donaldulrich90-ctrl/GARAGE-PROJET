from django.urls import path

from . import views

urlpatterns = [
    path("", views.garage_list, name="garage_list"),
    path("nouveau/", views.garage_create, name="garage_create"),
    path("<int:pk>/modifier/", views.garage_edit, name="garage_edit"),
    path("<int:pk>/toggle/", views.garage_toggle, name="garage_toggle"),
    path("<int:pk>/fournisseur/", views.garage_supplier_create, name="garage_supplier_create"),
]
