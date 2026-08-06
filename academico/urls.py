from django.urls import path

from administracion.views import anio_escolar_create, anio_escolar_list, anio_escolar_update
from .views import area_competencia_create, area_competencia_delete, area_competencia_list, competencia_create, competencia_delete, competencia_list, competencia_update, docentemateria_create, docentemateria_delete, docentemateria_list, docentemateria_update, registrar_calificaciones, cerrar_anio_escolar
from . import views


urlpatterns = [
    path(
        'calificaciones/<int:inscripcion_id>/<int:asignatura_id>/',
        registrar_calificaciones,
        name='registrar_calificaciones'
    ),

path(
    'ajax/asignaturas-por-grado/<int:grado_id>/',
    views.ajax_asignaturas_por_grado,
    name='ajax_asignaturas_por_grado'
),


# academico/urls.py
path(
    'grados/<int:grado_id>/asignaturas/',
    views.grado_asignaturas,
    name='grado_asignaturas'
),

  path('niveles/', views.nivel_list, name='nivel_list'),
    path('niveles/nuevo/', views.nivel_create, name='nivel_create'),
    path('niveles/<int:pk>/editar/', views.nivel_update, name='nivel_update'),
    path('niveles/<int:pk>/eliminar/', views.nivel_delete, name='nivel_delete'),

# academico/urls.py
path(
    'grados/<int:grado_id>/estudiantes/',
    views.grado_estudiantes,
    name='grado_estudiantes'
),


    path('grados/', views.grado_list, name='grado_list'),
    path('grados/nuevo/', views.grado_create, name='grado_create'),
    path('grados/<int:pk>/editar/', views.grado_update, name='grado_update'),
    path('grados/<int:pk>/eliminar/', views.grado_delete, name='grado_delete'),


    path('secciones/', views.seccion_list, name='seccion_list'),
    path('secciones/nueva/', views.seccion_create, name='seccion_create'),
    path('secciones/<int:pk>/editar/', views.seccion_update, name='seccion_update'),
    path('secciones/<int:pk>/eliminar/', views.seccion_delete, name='seccion_delete'),


    path('areas/', views.area_list, name='area_list'),
    path('areas/nueva/', views.area_create, name='area_create'),
    path('areas/<int:pk>/editar/', views.area_update, name='area_update'),
    path('areas/<int:pk>/eliminar/', views.area_delete, name='area_delete'),


    path('asignaturas/', views.asignatura_list, name='asignatura_list'),
    path('asignaturas/nueva/', views.asignatura_create, name='asignatura_create'),
    path('asignaturas/<int:pk>/editar/', views.asignatura_update, name='asignatura_update'),
    path('asignaturas/<int:pk>/eliminar/', views.asignatura_delete, name='asignatura_delete'),


    path(
        'grado-asignaturas/',
        views.grado_asignatura_list,
        name='grado_asignatura_list'
    ),
    path(
        'grado-asignaturas/nueva/',
        views.grado_asignatura_create,
        name='grado_asignatura_create'
    ),
    path(
        'grado-asignaturas/<int:pk>/eliminar/',
        views.grado_asignatura_delete,
        name='grado_asignatura_delete'
    ),

  

path('competencias/', competencia_list, name='competencia_list'),
path('competencias/nueva/', competencia_create, name='competencia_create'),
path('competencias/<int:pk>/editar/', competencia_update, name='competencia_update'),
path('competencias/<int:pk>/eliminar/', competencia_delete, name='competencia_delete'),

path('area-competencias/', area_competencia_list, name='area_competencia_list'),
path('area-competencias/nueva/', area_competencia_create, name='area_competencia_create'),
path('area-competencias/<int:pk>/eliminar/', area_competencia_delete, name='area_competencia_delete'),

    path('periodos/cerrar-todos/', views.cerrar_todos_los_periodos, name='cerrar_todos_periodos'),

    path('periodos/', views.periodo_list, name='periodo_list'),
    path('periodos/nuevo/', views.periodo_create, name='periodo_create'),
    path('periodos/<int:pk>/editar/', views.periodo_update, name='periodo_update'),
    path('periodos/<int:pk>/eliminar/', views.periodo_delete, name='periodo_delete'),

    path('docente-materia/', docentemateria_list, name='docentemateria_list'),
path('docente-materia/nuevo/', docentemateria_create, name='docentemateria_create'),
path('docente-materia/<int:pk>/editar/', docentemateria_update, name='docentemateria_update'),
path('docente-materia/<int:pk>/eliminar/', docentemateria_delete, name='docentemateria_delete'),


    path('anio-escolar/', anio_escolar_list, name='anio_escolar_list'),
    path('anio-escolar/crear/', anio_escolar_create, name='anio_escolar_create'),
    path('anio-escolar/<int:pk>/editar/', anio_escolar_update, name='anio_escolar_update'),
    path('anio-escolar/<int:pk>/cerrar/', views.cerrar_anio_escolar, name='cerrar_anio_escolar'),

]
