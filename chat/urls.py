from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # Côté garage (staff / mécaniciens)
    path("", views.garage_inbox, name="garage_inbox"),
    path("fournisseur/<int:supplier_pk>/", views.garage_thread, name="garage_thread"),
    # Côté fournisseur
    path("espace-fournisseur/", views.supplier_inbox, name="supplier_inbox"),
    path("espace-fournisseur/garage/<int:garage_pk>/", views.supplier_thread, name="supplier_thread"),
]
