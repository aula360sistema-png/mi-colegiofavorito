from django.urls import path

from reportes.views import asistencia, calificaciones, carga_academica, principal

app_name = 'reportes'

urlpatterns = [
    path('', principal.reportes, name='reportes'),
    path(
        'listado-seccion/imprimir/',
        principal.print_listado_seccion,
        name='print_listado_seccion',
    ),
    path(
        'asistencia/',
        asistencia.reporte_asistencia,
        name='reporte_asistencia',
    ),
    path(
        'asistencia/imprimir/',
        asistencia.print_asistencia,
        name='print_asistencia',
    ),
    path(
        'carga-academica/',
        carga_academica.reporte_carga_academica,
        name='reporte_carga_academica',
    ),
    path(
        'carga-academica/imprimir/',
        carga_academica.print_carga_academica,
        name='print_carga_academica',
    ),
    path(
        'calificaciones/',
        calificaciones.reporte_calificaciones,
        name='reporte_calificaciones',
    ),
    path(
        'calificaciones/imprimir/',
        calificaciones.print_calificaciones,
        name='print_calificaciones',
    ),
    path(
        'boleta/<int:inscripcion_id>/<int:periodo_id>/',
        calificaciones.boleta_periodo,
        name='boleta_periodo',
    ),
    path(
        'boleta/imprimir/',
        calificaciones.print_boleta,
        name='print_boleta',
    ),
]