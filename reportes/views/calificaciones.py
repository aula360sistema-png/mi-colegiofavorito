"""Vistas del reporte de calificaciones por período (planilla y boleta).

- reporte_calificaciones  : pantalla con filtros (año, grado, sección, período).
- print_calificaciones    : planilla imprimible del grado/sección en un período.
- boleta_periodo          : detalle por estudiante del período (competencias).
- print_boleta            : boleta imprimible por estudiante.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from academico.models import Grado, Periodo, Seccion
from core.decorators import centro_required, role_required
from core.utils.anio import obtener_anio_activo
from estudiantes.models import Inscripcion

from reportes.services import calificaciones as s_calificaciones
from reportes.services.base import anio_de, es_rol_gestion, secciones_permitidas
from reportes.views import base as base_views

ROLES = ('director', 'secretaria', 'admin', 'superadmin', 'docente')


def _seccion_accesible(centro, anio, user, seccion):
    """True si el usuario puede consultar la sección en el año elegido."""
    if es_rol_gestion(user):
        return True
    permitidas = secciones_permitidas(centro, anio, user)
    return permitidas.filter(seccion=seccion).exists()


@login_required
@centro_required
@role_required(*ROLES)
def reporte_calificaciones(request):
    """Planilla de calificaciones del grado/sección en un período."""
    centro = request.centro
    anios, anio_actual = base_views.contexto_base(centro, obtener_anio_activo(centro))

    sel_anio = request.GET.get('anio', '') or (
        str(anio_actual.id) if anio_actual else ''
    )
    anio = anio_de(centro, sel_anio)
    sel_grado = request.GET.get('grado', '')
    sel_seccion = request.GET.get('seccion', '')
    sel_periodo = request.GET.get('periodo', '')

    grados = base_views.graduados_visibles(centro, anio, request.user)
    secciones_del_grado = base_views.secciones_de_grado(
        centro, sel_grado, anio, request.user
    )
    periodos = Periodo.objects.filter(centro=centro).order_by('orden')

    resultado = None
    if (
        anio
        and sel_grado
        and sel_seccion
        and sel_periodo
    ):
        grado = get_object_or_404(Grado, pk=sel_grado)
        seccion = get_object_or_404(
            Seccion.objects.filter(centro=centro), pk=sel_seccion
        )
        periodo = get_object_or_404(Periodo, pk=sel_periodo, centro=centro)

        if not _seccion_accesible(centro, anio, request.user, seccion):
            return render(request, '403.html', status=403)

        inscripciones = base_views.inscripciones_visibles(
            centro,
            anio,
            request.user,
            grado_id=sel_grado,
            seccion_id=sel_seccion,
        )

        planilla = s_calificaciones.planilla_calificaciones(
            centro, anio, grado, seccion, periodo, inscripciones
        )
        planilla['grado'] = grado
        planilla['seccion'] = seccion
        planilla['anio'] = anio
        planilla['periodo'] = periodo
        resultado = planilla

    return render(request, 'reportes/calificaciones.html', {
        'centro': centro,
        'anios': anios,
        'grados': grados,
        'periodos': periodos,
        'secciones_del_grado': secciones_del_grado,
        'anio_actual': anio_actual,
        'sel_anio': str(sel_anio or ''),
        'sel_grado': sel_grado,
        'sel_seccion': sel_seccion,
        'sel_periodo': str(sel_periodo or ''),
        'resultado': resultado,
        'es_gestion': es_rol_gestion(request.user),
    })


@login_required
@centro_required
@role_required(*ROLES)
def print_calificaciones(request):
    """Planilla imprimible de calificaciones del grado/sección en un período."""
    centro = request.centro
    anio = anio_de(centro, request.GET.get('anio', ''))
    grado_id = request.GET.get('grado', '')
    seccion_id = request.GET.get('seccion', '')
    periodo_id = request.GET.get('periodo', '')

    contexto = {
        'centro': centro,
        'anio': anio,
        'fecha_emision': timezone.localdate(),
    }
    if not anio:
        contexto['error'] = 'No hay año escolar seleccionado ni año activo.'
        return render(request, 'reportes/error_print.html', contexto)
    if not (grado_id.isdigit() and seccion_id.isdigit() and periodo_id.isdigit()):
        contexto['error'] = 'Faltan filtros: grado, sección y período.'
        return render(request, 'reportes/error_print.html', contexto)

    grado = get_object_or_404(Grado, pk=grado_id)
    seccion = get_object_or_404(Seccion.objects.filter(centro=centro), pk=seccion_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id, centro=centro)

    if not _seccion_accesible(centro, anio, request.user, seccion):
        return render(request, '403.html', status=403)

    inscripciones = base_views.inscripciones_visibles(
        centro, anio, request.user, grado_id=grado_id, seccion_id=seccion_id
    )
    planilla = s_calificaciones.planilla_calificaciones(
        centro, anio, grado, seccion, periodo, inscripciones
    )
    contexto.update({
        'grado': grado,
        'seccion': seccion,
        'anio_escolar': anio,
        'periodo': periodo,
        'asignaturas': planilla['asignaturas'],
        'filas': planilla['filas'],
        'promedios_por_asignatura': planilla['promedios_por_asignatura'],
        'nota_minima': planilla['nota_minima'],
        'total': len(planilla['filas']),
    })
    return render(request, 'reportes/calificaciones_planilla_print.html', contexto)


@login_required
@centro_required
@role_required(*ROLES)
def boleta_periodo(request, inscripcion_id, periodo_id):
    """Boleta de un estudiante para un período concreto."""
    centro = request.centro
    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            'estudiante', 'grado', 'grado__nivel', 'seccion', 'anio_escolar'
        ),
        pk=inscripcion_id,
        centro=centro,
    )
    periodo = get_object_or_404(Periodo, pk=periodo_id, centro=centro)
    anio = inscripcion.anio_escolar

    if not _seccion_accesible(centro, anio, request.user, inscripcion.seccion):
        return render(request, '403.html', status=403)

    boleta = s_calificaciones.boleta_periodo(inscripcion, anio, periodo, centro)

    return render(request, 'reportes/boleta_periodo.html', {
        'centro': centro,
        **boleta,
    })


@login_required
@centro_required
@role_required(*ROLES)
def print_boleta(request):
    """Boleta imprimible del período de un estudiante."""
    centro = request.centro
    inscripcion_id = request.GET.get('inscripcion_id', '')
    periodo_id = request.GET.get('periodo_id', '')

    contexto = {'centro': centro, 'fecha_emision': timezone.localdate()}
    if not (inscripcion_id.isdigit() and periodo_id.isdigit()):
        contexto['error'] = 'Faltan datos del estudiante o del período.'
        return render(request, 'reportes/error_print.html', contexto)

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            'estudiante', 'grado', 'grado__nivel', 'seccion', 'anio_escolar'
        ),
        pk=inscripcion_id,
        centro=centro,
    )
    periodo = get_object_or_404(Periodo, pk=periodo_id, centro=centro)
    anio = inscripcion.anio_escolar

    if not _seccion_accesible(centro, anio, request.user, inscripcion.seccion):
        return render(request, '403.html', status=403)

    contexto.update(
        s_calificaciones.boleta_periodo(inscripcion, anio, periodo, centro)
    )
    return render(request, 'reportes/boleta_estudiante_print.html', contexto)