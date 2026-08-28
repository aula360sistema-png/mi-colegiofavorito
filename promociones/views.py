"""Vistas del módulo de promociones.

Panel de control (dashboard/semáforo), recuperación pedagógica y
extraordinario. Son proceso de orquestación: leen datos de los dominios
académicos pero no son dueñas de ningún modelo propio.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from academico.models import PeriodoAnio
from core.decorators import centro_required, role_required
from core.models import AnioEscolar, CierreAnio, ConfiguracionCentro
from core.utils.anio import obtener_anio_activo

from estudiantes.models import Inscripcion

from .services.recuperacion import (
    asignaturas_reprobadas_con_docente,
    nota_minima_estudiante,
)


def _estado_cierre_anio(centro):
    """Arma el semáforo de las 6 etapas del cierre para el año activo o el último cerrado.

    Reutiliza datos ya existentes: PeriodoAnio, Inscripcion.estado_final,
    CierreAnio, AnioEscolar. No hace ningún cálculo nuevo de negocio.
    """
    from core.models import CierreAnio

    anio = obtener_anio_activo(centro)
    if not anio:
        ultimo_cierre = CierreAnio.objects.filter(
            anio_escolar__centro=centro
        ).select_related('anio_escolar').order_by('-fecha').first()
        if ultimo_cierre:
            anio = ultimo_cierre.anio_escolar
        else:
            return None

    periodos = PeriodoAnio.objects.filter(
        anio_escolar=anio, periodo__es_completivo=False,
        periodo__es_extraordinario=False
    )
    periodos_total = periodos.count()
    periodos_cerrados = periodos.filter(cerrado=True).count()

    completivo_periodos = PeriodoAnio.objects.filter(
        anio_escolar=anio, periodo__es_completivo=True
    )
    completivo_abierto = completivo_periodos.filter(cerrado=False).exists()
    completivo_existe = completivo_periodos.exists()

    extraordinario_periodos = PeriodoAnio.objects.filter(
        anio_escolar=anio, periodo__es_extraordinario=True
    )
    extraordinario_abierto = extraordinario_periodos.filter(
        cerrado=False
    ).exists()
    extraordinario_existe = extraordinario_periodos.exists()

    inscripciones = Inscripcion.objects.filter(
        centro=centro, anio_escolar=anio
    )
    total_inscripciones = inscripciones.count()
    con_boletin = inscripciones.exclude(estado_final='pendiente').count()
    en_recuperacion = inscripciones.filter(estado_final='recuperacion').count()
    reprobados = inscripciones.filter(estado_final='reprobado').count()
    condicionales = inscripciones.filter(
        estado_final='promocion_condicional'
    ).count()
    sin_calificacion = inscripciones.filter(estado_final='sin_calificacion').count()

    cierre = CierreAnio.objects.filter(anio_escolar=anio).first()
    anio_siguiente_existe = AnioEscolar.objects.filter(
        centro=centro, fecha_inicio__gt=anio.fecha_fin
    ).exists()

    return {
        'anio': anio,
        'periodos_total': periodos_total,
        'periodos_cerrados': periodos_cerrados,
        'periodos_ok': periodos_total > 0 and periodos_cerrados == periodos_total,

        'boletines_total': total_inscripciones,
        'boletines_generados': con_boletin,
        'boletines_ok': total_inscripciones == 0 or con_boletin == total_inscripciones,

        'sin_calificacion': sin_calificacion,

        'en_recuperacion': en_recuperacion,
        'completivo_existe': completivo_existe,
        'completivo_abierto': completivo_abierto,
        'completivo_ok': en_recuperacion == 0,

        'reprobados': reprobados,
        'condicionales': condicionales,
        'extraordinario_existe': extraordinario_existe,
        'extraordinario_abierto': extraordinario_abierto,
        'extraordinario_ok': reprobados == 0,

        'anio_cerrado': anio.cerrado,
        'cierre': cierre,

        'anio_siguiente_existe': anio_siguiente_existe,
        'promocion_ejecutada': cierre is not None,

        'sin_calificacion_bloquea': sin_calificacion > 0,
    }


@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def promociones_dashboard(request):
    centro = request.centro
    estado = _estado_cierre_anio(centro)
    return render(request, 'promociones/dashboard.html', {
        'estado': estado,
    })


# ---------------------------------------------------------------------------
# Vista de estudiantes en recuperación – detalle de quién debe qué
# ---------------------------------------------------------------------------

@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def promociones_recuperacion(request):
    centro = request.centro
    anio = obtener_anio_activo(centro)
    if not anio:
        return redirect('promociones:dashboard')

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)

    inscripciones = Inscripcion.objects.filter(
        centro=centro, anio_escolar=anio, estado_final='recuperacion'
    ).select_related('estudiante', 'grado', 'seccion', 'grado__nivel')

    filas = []
    for ins in inscripciones:
        nota_minima = nota_minima_estudiante(ins, configuracion)
        if nota_minima is None:
            continue
        try:
            detalle = asignaturas_reprobadas_con_docente(
                ins, centro, anio, nota_minima
            )
        except ValueError:
            continue

        docentes_unicos = []
        for d in detalle:
            if d['docente'] and d['docente'] not in docentes_unicos:
                docentes_unicos.append(d['docente'])

        filas.append({
            'inscripcion': ins,
            'asignaturas_pendientes': detalle,
            'docentes': docentes_unicos,
        })

    return render(request, 'promociones/recuperacion.html', {
        'anio': anio,
        'filas': filas,
    })


# ---------------------------------------------------------------------------
# Vista de estudiantes reprobados – extraordinario
# ---------------------------------------------------------------------------

@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def promociones_extraordinario(request):
    centro = request.centro
    anio = obtener_anio_activo(centro)
    if not anio:
        return redirect('promociones:dashboard')

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)

    inscripciones = Inscripcion.objects.filter(
        centro=centro, anio_escolar=anio, estado_final='reprobado'
    ).select_related('estudiante', 'grado', 'seccion', 'grado__nivel')

    filas = []
    for ins in inscripciones:
        nota_minima = nota_minima_estudiante(ins, configuracion)
        if nota_minima is None:
            continue
        try:
            detalle = asignaturas_reprobadas_con_docente(
                ins, centro, anio, nota_minima
            )
        except ValueError:
            continue

        docentes_unicos = []
        for d in detalle:
            if d['docente'] and d['docente'] not in docentes_unicos:
                docentes_unicos.append(d['docente'])

        filas.append({
            'inscripcion': ins,
            'asignaturas_pendientes': detalle,
            'docentes': docentes_unicos,
        })

    return render(request, 'promociones/extraordinario.html', {
        'anio': anio,
        'filas': filas,
    })
