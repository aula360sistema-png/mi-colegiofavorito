from django.urls import path
from . import views

urlpatterns = [
    path('', views.estudiante_list, name='estudiante_list'),
    path('nuevo/', views.estudiante_create, name='estudiante_create'),
    path('<int:pk>/', views.estudiante_detail, name='estudiante_detail'),
    path('<int:pk>/editar/', views.estudiante_update, name='estudiante_update'),
    path('<int:pk>/eliminar/', views.estudiante_delete, name='estudiante_delete'),
    path('<int:estudiante_id>/inscribir/', views.inscribir_estudiante, name='inscribir_estudiante'),
    path(
    '<int:estudiante_id>/inscribir-avanzado/',
    views.inscribir_estudiante_avanzado,
    name='inscribir_estudiante_avanzado'
),
path(
    'inscripcion/<int:inscripcion_id>/asignaturas/',
    views.inscripcion_asignaturas,
    name='inscripcion_asignaturas'
),

path(
    'ajax/cargar-secciones/',
    views.ajax_cargar_secciones,
    name='ajax_cargar_secciones'
),

]
