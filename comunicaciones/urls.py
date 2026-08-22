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

    # Comunicados / anuncios por seccion
    path('comunicados/', views.comunicado_list, name='comunicado_list'),
    path('comunicados/nuevo/', views.comunicado_create, name='comunicado_create'),
    path('comunicados/<int:pk>/editar/', views.comunicado_update, name='comunicado_update'),
    path('comunicados/<int:pk>/eliminar/', views.comunicado_delete, name='comunicado_delete'),

    # Portales de solo lectura
    path('mis-comunicados/', views.estudiante_comunicados, name='estudiante_comunicados'),
    path('comunicados-familia/', views.tutor_comunicados, name='tutor_comunicados'),
]
