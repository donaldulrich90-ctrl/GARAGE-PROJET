from django.urls import path

from . import views

urlpatterns = [
    path("", views.expense_list, name="expense_list"),
    path("nouveau/", views.expense_create, name="expense_create"),
    path("<int:pk>/modifier/", views.expense_edit, name="expense_edit"),
    path("<int:pk>/supprimer/", views.expense_delete, name="expense_delete"),
]
