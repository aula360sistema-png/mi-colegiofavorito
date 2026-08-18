from django.urls import path
from . import views

urlpatterns = [
    path('', views.estudiante_list, name='estudiante_list'),
    path('inicio/', views.estudiante_inicio, name='estudiante_inicio'),
    path('nuevo/', views.estudiante_create, name='estudiante_create'),
    path('<int:pk>/', views.estudiante_detail, name='estudiante_detail'),
    path('<int:pk>/editar/', views.estudiante_update, name='estudiante_update'),
    path('<int:pk>/eliminar/', views.estudiante_delete, name='estudiante_delete'),
    path('<int:estudiante_id>/inscribir/', views.inscribir_estudiante_avanzado, name='inscribir_estudiante'),
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

path(
    'historial/',
    views.historial_estudiantes,
    name='historial_estudiantes'
),

path(
    'constancias/',
    views.constancias,
    name='constancias'
),

path(
    'constancia/<int:pk>/',
    views.constancia_estudiante,
    name='constancia_estudiante'
),

path(
    '<int:pk>/cambiar-estado/',
    views.cambiar_estado_estudiante,
    name='cambiar_estado_estudiante'
),

path(
    '<int:pk>/kardex/imprimir/',
    views.kardex_imprimir,
    name='kardex_imprimir'
),

path(
    '<int:pk>/observaciones/agregar/',
    views.agregar_observacion_estudiante,
    name='agregar_observacion_estudiante'
),

path(
    'disciplina/',
    views.disciplina,
    name='disciplina'
),

path(
    'disciplina/registrar/',
    views.disciplina_registrar,
    name='disciplina_registrar'
),

path(
    'disciplina/<int:pk>/eliminar/',
    views.disciplina_eliminar,
    name='disciplina_eliminar'
),

path(
    'inicio/solicitudes/',
    views.estudiante_solicitudes,
    name='estudiante_solicitudes'
),

path(
    'inicio/solicitudes/<int:pk>/pagar/',
    views.estudiante_solicitud_pagar,
    name='estudiante_solicitud_pagar'
),

path(
    'inicio/historial-clinico/',
    views.estudiante_historial_clinico,
    name='estudiante_historial_clinico'
),

path(
    'solicitudes/',
    views.solicitudes_certificados_list,
    name='solicitudes_certificados'
),

path(
    'solicitudes/<int:pk>/aprobar/',
    views.solicitud_aprobar,
    name='solicitud_aprobar'
),

path(
    'solicitudes/<int:pk>/rechazar/',
    views.solicitud_rechazar,
    name='solicitud_rechazar'
),

path(
    'solicitudes/<int:pk>/cobrar/',
    views.solicitud_cobrar,
    name='solicitud_cobrar'
),

path(
    'solicitudes/<int:pk>/entregar/',
    views.solicitud_entregar,
    name='solicitud_entregar'
),

path(
    'solicitudes/<int:pk>/anular/',
    views.solicitud_anular,
    name='solicitud_anular'
),

path(
    'historial-clinico/',
    views.historial_clinico_list,
    name='historial_clinico_list'
),

path(
    'historial-clinico/<int:pk>/',
    views.historial_clinico_detalle,
    name='historial_clinico_detalle'
),

path(
    'historial-clinico/<int:pk>/editar/',
    views.historial_clinico_editar,
    name='historial_clinico_editar'
),

path(
    'historial-clinico/<int:pk>/registro/',
    views.registro_salud_crear,
    name='registro_salud_crear'
),

path(
    'registro-salud/<int:pk>/eliminar/',
    views.registro_salud_eliminar,
    name='registro_salud_eliminar'
),

]
