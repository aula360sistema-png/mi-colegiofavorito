from django.urls import path

from . import views

app_name = 'entrenamiento'

urlpatterns = [
    path('', views.inicio, name='inicio'),

    path('tramos/', views.tramo_list, name='tramo_list'),
    path('tramos/nuevo/', views.tramo_create, name='tramo_create'),
    path('tramos/<int:pk>/editar/', views.tramo_update, name='tramo_update'),
    path('tramos/<int:pk>/eliminar/', views.tramo_delete, name='tramo_delete'),

    path('destrezas/', views.destreza_list, name='destreza_list'),
    path('destrezas/nueva/', views.destreza_create, name='destreza_create'),
    path('destrezas/<int:pk>/editar/', views.destreza_update, name='destreza_update'),
    path('destrezas/<int:pk>/eliminar/', views.destreza_delete, name='destreza_delete'),

    path('unidades/', views.unidad_list, name='unidad_list'),
    path('unidades/nueva/', views.unidad_create, name='unidad_create'),
    path('unidades/<int:pk>/editar/', views.unidad_update, name='unidad_update'),
    path('unidades/<int:pk>/eliminar/', views.unidad_delete, name='unidad_delete'),

    path('ejercicios/', views.ejercicio_list, name='ejercicio_list'),
    path('ejercicios/nuevo/', views.ejercicio_create, name='ejercicio_create'),
    path('ejercicios/<int:pk>/', views.ejercicio_detail, name='ejercicio_detail'),
    path('ejercicios/<int:pk>/eliminar/', views.ejercicio_delete, name='ejercicio_delete'),

    path('diagnosticos/', views.diagnostico_list, name='diagnostico_list'),
    path('diagnosticos/nuevo/', views.diagnostico_create, name='diagnostico_create'),
    path('diagnosticos/<int:pk>/', views.diagnostico_detail, name='diagnostico_detail'),
    path('diagnosticos/<int:pk>/eliminar/', views.diagnostico_delete, name='diagnostico_delete'),

    path('sesiones/', views.sesion_list, name='sesion_list'),
    path('sesiones/nueva/', views.sesion_create, name='sesion_create'),
    path('sesiones/<int:pk>/', views.sesion_detail, name='sesion_detail'),
    path('sesiones/<int:pk>/eliminar/', views.sesion_delete, name='sesion_delete'),

    path('metricas/', views.metrica_list, name='metrica_list'),
    path('metricas/<int:pk>/', views.metrica_detail, name='metrica_detail'),

    path('planes/', views.plan_list, name='plan_list'),
    path('planes/nuevo/', views.plan_create, name='plan_create'),
    path('planes/<int:pk>/', views.plan_detail, name='plan_detail'),
    path('planes/<int:pk>/estado/', views.plan_update_estado, name='plan_update_estado'),
    path('planes/<int:pk>/eliminar/', views.plan_delete, name='plan_delete'),

    path('api/destrezas-por-tramo/', views.api_destrezas_por_tramo, name='api_destrezas_por_tramo'),
]
