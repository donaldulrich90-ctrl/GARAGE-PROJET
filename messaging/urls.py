from django.urls import path

from . import views

urlpatterns = [
    path('envoyer/<int:client_pk>/', views.log_and_redirect, name='wa_send'),
    path('historique/', views.history, name='wa_history'),
    path('broadcast/', views.broadcast, name='wa_broadcast'),
    path('templates/', views.templates_list, name='wa_templates'),
    path('webhook/whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
]
