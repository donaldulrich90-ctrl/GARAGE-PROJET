from django.urls import path

from . import views

urlpatterns = [
    path('', views.insurance_list, name='insurance_list'),
    path('ajouter/', views.insurance_create, name='insurance_create'),
    path('<int:pk>/', views.insurance_detail, name='insurance_detail'),
    path('<int:pk>/modifier/', views.insurance_update, name='insurance_update'),
    path('<int:pk>/supprimer/', views.insurance_delete, name='insurance_delete'),
    path('<int:insurance_pk>/sinistres/ajouter/', views.claim_create, name='claim_create'),
    path('sinistres/', views.claim_list, name='claim_list'),
    path('sinistres/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('sinistres/<int:pk>/modifier/', views.claim_update, name='claim_update'),
]
