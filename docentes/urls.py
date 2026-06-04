# docentes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.docente_list, name='docente_list'),
    path('crear/', views.docente_create, name='docente_create'),
    path('editar/<int:pk>/', views.docente_update, name='docente_update'),
    path('eliminar/<int:pk>/', views.docente_delete, name='docente_delete'),
    path('detalle/<int:pk>/', views.docente_detail, name='docente_detail'),

     path('dashboard/', views.dashboard_docente, name='dashboard_docente'),
        path( 'asignacion/<int:asignacion_id>/estudiantes/',   views.docente_estudiantes,
        name='docente_estudiantes'
    ),

  path(
        'asignacion/<int:asignacion_id>/guardar-notas/',
        views.guardar_notas_ajax,
        name='guardar_notas_ajax'
    ),
        
    path(
        'asignacion/<int:asignacion_id>/calificar/',
        views.calificar_tabla,
        name='calificar_tabla'
    )
]
