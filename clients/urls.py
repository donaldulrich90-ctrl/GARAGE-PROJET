from django.urls import path

from . import views

urlpatterns = [
    path('', views.ClientListView.as_view(), name='client_list'),
    path('nouveau/', views.ClientCreateView.as_view(), name='client_create'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/modifier/', views.ClientUpdateView.as_view(), name='client_update'),
    path('<int:client_pk>/vehicule/ajouter/', views.VehicleCreateView.as_view(), name='vehicle_create_for_client'),
]
