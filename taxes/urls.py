from django.urls import path

from . import views

app_name = 'taxes'

urlpatterns = [
    path('', views.tax_list, name='tax_list'),
    path('ajouter/', views.tax_create, name='tax_create'),
    path('<int:pk>/', views.tax_detail, name='tax_detail'),
    path('<int:pk>/modifier/', views.tax_update, name='tax_update'),
    path('<int:pk>/supprimer/', views.tax_delete, name='tax_delete'),
    path('<int:pk>/payer/', views.tax_mark_paid, name='tax_mark_paid'),
]
