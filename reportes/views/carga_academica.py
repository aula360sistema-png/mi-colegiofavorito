"""Vistas de la carga académica de docentes (pantalla e impresión)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.utils.anio import obtener_anio_activo
from docentes.models import Docente

from reportes.services.base import es_rol_gestion
from reportes.services.carga_academica import carga_academica
from reportes.views import base as base_views

ROLES = ('director', 'secretaria', 'admin', 'superadmin', 'docente')


@login_required
@centro_required
@role_required(*ROLES)
def reporte_carga_academica(request):
    """Pantalla para consultar e imprimir la carga académica de docentes."""
    centro = request.centro
    anios, anio_actual = base_views.contexto_base(centro, obtener_anio_activo(centro))

    sel_anio = request.GET.get('anio', '') or (
        str(anio_actual.id) if anio_actual else ''
    )
    sel_grado = request.GET.get('grado', '')
    sel_docente = request.GET.get('docente_id', '')

    anio, filas = carga_academica(
        centro, sel_anio, sel_grado, sel_docente, user=request.user
    )

    if es_rol_gestion(request.user):
        docentes = Docente.objects.filter(centro=centro, estado='activo').order_by(
            'primer_apellido', 'primer_nombre'
        )
    else:
        docentes = Docente.objects.filter(centro=centro).order_by(
            'primer_apellido', 'primer_nombre'
        )

    grados = base_views.graduados_visibles(centro, anio, request.user)

    return render(request, 'reportes/carga_academica.html', {
        'centro': centro,
        'anios': anios,
        'grados': grados,
        'docentes': docentes,
        'anio_actual': anio_actual,
        'sel_anio': sel_anio,
        'sel_grado': sel_grado,
        'sel_docente': str(sel_docente),
        'anio': anio,
        'filas': filas,
        'total_asignaciones': sum(len(f['asignaciones']) for f in filas),
        'fecha_emision': timezone.localdate(),
    })


@login_required
@centro_required
@role_required(*ROLES)
def print_carga_academica(request):
    """Impresión de la carga académica de docentes."""
    centro = request.centro
    anio, filas = carga_academica(
        centro,
        request.GET.get('anio', ''),
        request.GET.get('grado', ''),
        request.GET.get('docente_id', ''),
        user=request.user,
    )

    contexto = {
        'centro': centro,
        'anio': anio,
        'filas': filas,
        'total_asignaciones': sum(len(f['asignaciones']) for f in filas),
        'fecha_emision': timezone.localdate(),
    }
    if not anio:
        contexto['error'] = 'No hay año escolar seleccionado ni año activo.'
        return render(request, 'reportes/error_print.html', contexto)

    return render(request, 'reportes/carga_academica_print.html', contexto)