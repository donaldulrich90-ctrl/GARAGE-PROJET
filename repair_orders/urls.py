from django.urls import path

from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('nouveau/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/modifier/', views.OrderUpdateView.as_view(), name='order_update'),
    path('<int:pk>/statut/<str:status>/', views.ChangeStatusView.as_view(), name='order_status'),
    path('<int:pk>/tache/ajouter/', views.AddTaskView.as_view(), name='task_add'),
    path('<int:order_pk>/tache/<int:pk>/supprimer/', views.DeleteTaskView.as_view(), name='task_delete'),
    path('<int:pk>/piece/ajouter/', views.AddPartView.as_view(), name='part_add'),
    path('<int:order_pk>/piece/<int:pk>/retirer/', views.RemovePartView.as_view(), name='part_remove'),
    path('<int:pk>/facture/', views.CreateInvoiceView.as_view(), name='order_create_invoice'),
    path('<int:pk>/proforma/', views.ProformaPrintView.as_view(), name='order_proforma'),
]
