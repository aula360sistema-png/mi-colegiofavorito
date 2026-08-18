from django.urls import path

from . import views

app_name = 'comunicaciones'

urlpatterns = [
    path('', views.campania_list, name='campania_list'),
    path('nueva/', views.campania_create, name='campania_create'),
    path('<int:pk>/', views.campania_detail, name='campania_detail'),
    path('<int:pk>/editar/', views.campania_update, name='campania_update'),
    path('<int:pk>/enviar/', views.campania_enviar, name='campania_enviar'),
    path('<int:pk>/eliminar/', views.campania_delete, name='campania_delete'),
]
