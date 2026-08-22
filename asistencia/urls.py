from django.urls import path

from . import views

app_name = 'asistencia'

urlpatterns = [

    path(
        'tomar/',
        views.tomar_asistencia,
        name='tomar_asistencia'
    ),

    path(
        'estado-asistencia/',
        views.estado_asistencia,
        name='estado_asistencia'
    ),

    path(
        'resumen/',
        views.resumen_asistencia,
        name='resumen_asistencia'
    ),

    path(
        'dias-no-docencia/',
        views.dias_no_docencia,
        name='dias_no_docencia'
    ),

    path(
        'qr/generar/',
        views.asistencia_qr_generar,
        name='asistencia_qr_generar'
    ),

    path(
        'qr/datos/<int:inscripcion_id>/',
        views.qr_estudiante_data,
        name='qr_estudiante_data'
    ),

    path(
        'qr/escanear/',
        views.qr_escanear,
        name='qr_escanear'
    ),

    path(
        'biometrico/',
        views.asistencia_biometrico,
        name='asistencia_biometrico'
    ),

    path(
        'biometrico/api/',
        views.asistencia_biometrico_api,
        name='asistencia_biometrico_api'
    ),
]
