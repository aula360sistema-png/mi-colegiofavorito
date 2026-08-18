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
]
