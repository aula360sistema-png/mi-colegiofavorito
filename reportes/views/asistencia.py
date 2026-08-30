"""Vistas del reporte de asistencia (pantalla e impresión)."""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.models import AnioEscolar
from core.utils.anio import obtener_anio_activo

from reportes.services import asistencia as s_asistencia
from reportes.services.base import anio_de, es_rol_gestion
from reportes.views import base as base_views

ROLES = ('director', 'secretaria', 'admin', 'superadmin', 'docente')

logger = logging.getLogger(__name__)


@login_required
@centro_required
@role_required(*ROLES)
def reporte_asistencia(request):
    """Pantalla para consultar e imprimir asistencia por estudiante o sección."""
    centro = request.centro
    anios, anio_actual = base_views.contexto_base(centro, obtener_anio_activo(centro))

    tipo = request.GET.get('tipo') or 'seccion'
    sel_anio = request.GET.get('anio', '') or (
        str(anio_actual.id) if anio_actual else ''
    )
    sel_mes = request.GET.get('mes', '')
    sel_estudiante = request.GET.get('estudiante_id', '')
    sel_grado = request.GET.get('grado', '')
    sel_seccion = request.GET.get('seccion', '')

    anio = anio_de(centro, sel_anio)

    estudiantes = base_views.estudiantes_visibles(centro, anio, request.user)
    grados = base_views.graduados_visibles(centro, anio, request.user)
    secciones_del_grado = base_views.secciones_de_grado(
        centro, sel_grado, anio, request.user
    )

    resumen = None
    if anio and tipo == 'estudiante' and sel_estudiante:
        inscripcion = (
            base_views.inscripciones_visibles(
                centro, anio, request.user,
                grado_id='', seccion_id='',
            )
        )
        inscripcion = next(
            (
                i for i in inscripcion
                if str(i.estudiante_id) == sel_estudiante and i.anio_escolar_id == anio.id
            ),
            None,
        )
        if inscripcion:
            resumen = s_asistencia.resumen_asistencia_estudiante(
                inscripcion, anio, sel_mes
            )

    elif anio and tipo == 'seccion' and sel_grado:
        inscripciones = base_views.inscripciones_visibles(
            centro, anio, request.user,
            grado_id=sel_grado,
            seccion_id=sel_seccion,
        )
        resumen = s_asistencia.resumen_asistencia_seccion(inscripciones, anio, sel_mes)

    return render(request, 'reportes/asistencia.html', {
        'centro': centro,
        'anios': anios,
        'grados': grados,
        'estudiantes': estudiantes,
        'anio_actual': anio_actual,
        'tipo': tipo,
        'tipo_opciones': [
            ('seccion', 'Grado / Sección'),
            ('estudiante', 'Por estudiante'),
        ],
        'sel_anio': sel_anio,
        'sel_mes': sel_mes,
        'sel_estudiante': str(sel_estudiante),
        'sel_grado': sel_grado,
        'sel_seccion': sel_seccion,
        'secciones_del_grado': secciones_del_grado,
        'resumen': resumen,
        'MESES': s_asistencia.MESES_NOMBRES,
    })


@login_required
@centro_required
@role_required(*ROLES)
def print_asistencia(request):
    """Impresión de asistencia por estudiante o por grado/sección en un año."""
    centro = request.centro
    tipo = request.GET.get('tipo') or 'seccion'
    anio = anio_de(centro, request.GET.get('anio', ''))
    mes = request.GET.get('mes', '')

    contexto = {
        'centro': centro,
        'anio': anio,
        'mes': mes,
        'MESES': s_asistencia.MESES_NOMBRES,
        'MES': int(mes) if mes.isdigit() else None,
        'fecha_emision': timezone.localdate(),
        'tipo': tipo,
    }

    if not anio:
        contexto['error'] = 'No hay año escolar seleccionado ni año activo.'
        return render(request, 'reportes/error_print.html', contexto)

    if tipo == 'estudiante':
        inscripciones = base_views.inscripciones_visibles(
            centro,
            anio,
            request.user,
            grado_id='',
            seccion_id='',
        )
        inscripcion = next(
            (
                i for i in inscripciones
                if str(i.estudiante_id) == request.GET.get('estudiante_id', '')
            ),
            None,
        )
        if not inscripcion:
            contexto['error'] = (
                'El estudiante seleccionado no tiene inscripción en el año '
                'escolar elegido.'
            )
        else:
            contexto['inscripcion'] = inscripcion
            contexto['resumen'] = s_asistencia.resumen_asistencia_estudiante(
                inscripcion, anio, mes
            )
        return render(request, 'reportes/asistencia_print.html', contexto)

    inscripciones = base_views.inscripciones_visibles(
        centro,
        anio,
        request.user,
        grado_id=request.GET.get('grado', ''),
        seccion_id=request.GET.get('seccion', ''),
    )
    contexto['resumen'] = s_asistencia.resumen_asistencia_seccion(inscripciones, anio, mes)

    return render(request, 'reportes/asistencia_print.html', contexto)