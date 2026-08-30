"""Vistas principales de reportes: hub y listado imprimible de sección."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.utils.anio import obtener_anio_activo

from reportes.services.base import anio_de, es_rol_gestion
from reportes.services.metricas import obtener_metricas_reportes
from reportes.views import base as base_views

ROLES = ('director', 'secretaria', 'admin', 'superadmin', 'docente')


@login_required
@centro_required
@role_required(*ROLES)
def reportes(request):
    centro = request.centro

    anios, anio_actual = base_views.contexto_base(centro, obtener_anio_activo(centro))

    sel_anio = request.GET.get('anio') or (
        str(anio_actual.id) if anio_actual else ''
    )
    sel_grado = request.GET.get('grado', '')
    sel_seccion = request.GET.get('seccion', '')

    tab_activa = request.GET.get('tab', 'disponibles')
    if tab_activa not in ('disponibles', 'consultas', 'metricas'):
        tab_activa = 'disponibles'

    anio = anio_de(centro, sel_anio)

    metricas = obtener_metricas_reportes(centro)
    metricas['anio_actual'] = anio_actual

    grados = base_views.graduados_visibles(centro, anio, request.user)

    inscripciones = []
    if anio and sel_grado:
        inscripciones = base_views.inscripciones_visibles(
            centro, anio, request.user,
            grado_id=sel_grado,
            seccion_id=sel_seccion,
        )

    secciones_del_grado = base_views.secciones_de_grado(
        centro, sel_grado, anio, request.user
    )

    return render(request, 'reportes/reportes.html', {
        'centro': centro,
        **metricas,
        'anios': anios,
        'grados': grados,
        'secciones_del_grado': secciones_del_grado,
        'sel_anio': str(sel_anio or ''),
        'sel_grado': sel_grado,
        'sel_seccion': sel_seccion,
        'tab_activa': tab_activa,
        'es_gestion': es_rol_gestion(request.user),
        'inscripciones': inscripciones,
    })


@login_required
@centro_required
@role_required(*ROLES)
def print_listado_seccion(request):
    """Listado imprimible de estudiantes por grado/sección en un año."""
    centro = request.centro
    anio = anio_de(centro, request.GET.get('anio', ''))
    if not anio:
        return render(
            request,
            'reportes/error_print.html',
            {'centro': centro, 'error': 'No hay año escolar seleccionado ni año activo.'},
        )

    inscripciones = base_views.inscripciones_visibles(
        centro,
        anio,
        request.user,
        grado_id=request.GET.get('grado', ''),
        seccion_id=request.GET.get('seccion', ''),
    )

    primera = inscripciones[0] if inscripciones else None
    return render(
        request,
        'reportes/listado_seccion_print.html',
        {
            'centro': centro,
            'anio': anio,
            'grado': primera.grado if primera else None,
            'seccion': primera.seccion if primera else None,
            'inscripciones': inscripciones,
            'total': len(inscripciones),
            'fecha_emision': timezone.localdate(),
        },
    )