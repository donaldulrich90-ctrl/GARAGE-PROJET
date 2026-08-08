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
    path("profil/", views.ProfileView.as_view(), name="profile"),
    # Commandes reçues
    path("commandes/", views.OrderInboxView.as_view(), name="order_list"),
    path("commandes/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("commandes/<int:pk>/valider/", views.order_validate, name="order_validate"),
    path("commandes/<int:pk>/rejeter/", views.order_reject, name="order_reject"),
    path("commandes/<int:pk>/expedier/", views.order_ship, name="order_ship"),
]
