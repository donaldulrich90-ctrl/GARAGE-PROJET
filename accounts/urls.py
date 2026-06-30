from django.urls import path

from . import views

urlpatterns = [
    path("mot-de-passe/", views.password_change, name="password_change"),
    path("parametres/", views.garage_settings, name="garage_settings"),
    path("equipe/", views.user_list, name="user_list"),
    path("equipe/nouveau/", views.user_create, name="user_create"),
    path("equipe/<int:pk>/modifier/", views.user_edit, name="user_edit"),
    path("equipe/<int:pk>/mot-de-passe/", views.user_set_password, name="user_set_password"),
    path("equipe/<int:pk>/supprimer/", views.user_delete, name="user_delete"),
]
