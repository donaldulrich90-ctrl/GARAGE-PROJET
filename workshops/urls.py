from django.urls import path

from . import views

urlpatterns = [
    path('', views.SectionListView.as_view(), name='section_list'),
    path('nouveau/', views.SectionCreateView.as_view(), name='section_create'),
    path('<int:pk>/modifier/', views.SectionUpdateView.as_view(), name='section_update'),
    path('<int:pk>/activer/', views.SectionToggleView.as_view(), name='section_toggle'),
]
