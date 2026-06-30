from django.urls import path

from . import views

urlpatterns = [
    path('', views.PartListView.as_view(), name='part_list'),
    path('pieces/nouveau/', views.PartCreateView.as_view(), name='part_create'),
    path('pieces/<int:pk>/modifier/', views.PartUpdateView.as_view(), name='part_update'),
    path('fournisseurs/', views.SupplierListView.as_view(), name='supplier_list'),
    path('fournisseurs/nouveau/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('fournisseurs/<int:pk>/modifier/', views.SupplierUpdateView.as_view(), name='supplier_update'),
]
