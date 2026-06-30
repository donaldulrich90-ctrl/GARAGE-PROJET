from django.urls import path

from . import views

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='vehicle_list'),
    path('nouveau/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('<int:pk>/modifier/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
]
