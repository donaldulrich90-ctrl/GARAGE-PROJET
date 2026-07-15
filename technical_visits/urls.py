from django.urls import path

from . import views

urlpatterns = [
    path('', views.visit_list, name='visit_list'),
    path('ajouter/', views.visit_create, name='visit_create'),
    path('<int:pk>/', views.visit_detail, name='visit_detail'),
    path('<int:pk>/modifier/', views.visit_update, name='visit_update'),
    path('<int:pk>/supprimer/', views.visit_delete, name='visit_delete'),
]
