from django.db.models import Count, Q, Avg, DecimalField
from django.db.models.functions import Coalesce

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from .models import (
    DestrezaCognitiva,
    DiagnosticoCognitivo,
    Ejercicio,
    IntentoEjercicio,
    MetricaCognitiva,
    PlanRefuerzo,
    SesionEntrenamiento,
    TramoEdad,
    UnidadEntrenamiento,
)

TTL = 'CACHE_TTL_MEDIO'


# ---------------------------------------------------------------------------
# Cache domain helpers
# ---------------------------------------------------------------------------

def invalidar_entrenamiento(centro_id):
    invalidar_dominio(f'entrenamiento:{centro_id}')


def _version_entrenamiento(centro_id):
    return obtener_version(f'entrenamiento:{centro_id}')


# ---------------------------------------------------------------------------
# Catalog services (global, not per-center)
# ---------------------------------------------------------------------------

def tramos_disponibles():
    clave = f'entrenamiento_tramos:{obtener_version("entrenamiento_catalogo")}'
    return obtener_o_generar(
        clave,
        lambda: list(TramoEdad.objects.filter(activo=True).order_by('orden')),
        version=1,
        timeout=ttl('CACHE_TTL_LARGO'),
    )


def destrezas_por_tramo(tramo_id):
    clave = f'entrenamiento_destrezas:{tramo_id}:{obtener_version("entrenamiento_catalogo")}'
    return obtener_o_generar(
        clave,
        lambda: list(DestrezaCognitiva.objects.filter(
            tramo_id=tramo_id, activo=True
        ).order_by('orden')),
        version=1,
        timeout=ttl('CACHE_TTL_LARGO'),
    )


def unidades_por_tramo(tramo_id):
    clave = f'entrenamiento_unidades:{tramo_id}:{obtener_version("entrenamiento_catalogo")}'
    return obtener_o_generar(
        clave,
        lambda: list(UnidadEntrenamiento.objects.filter(
            tramo_id=tramo_id, activo=True
        ).select_related('tramo').prefetch_related('destrezas').order_by('numero')),
        version=1,
        timeout=ttl('CACHE_TTL_LARGO'),
    )


def ejercicios_por_unidad(unidad_id):
    clave = f'entrenamiento_ejercicios:{unidad_id}:{obtener_version("entrenamiento_catalogo")}'
    return obtener_o_generar(
        clave,
        lambda: list(Ejercicio.objects.filter(
            unidad_id=unidad_id, activo=True
        ).select_related('destreza').order_by('destreza__orden', 'dificultad')),
        version=1,
        timeout=ttl(TTL),
    )


def invalidar_catalogo():
    invalidar_dominio('entrenamiento_catalogo')


# ---------------------------------------------------------------------------
# Per-center services
# ---------------------------------------------------------------------------

def diagnosticos_del_centro(centro, anio_escolar):
    if not anio_escolar:
        return []
    clave = f'entrenamiento_diagnosticos:{centro.id}:{anio_escolar.id}:{_version_entrenamiento(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(DiagnosticoCognitivo.objects.filter(
            anio_escolar=anio_escolar,
            estudiante__inscripciones__anio_escolar=anio_escolar,
        ).select_related(
            'estudiante', 'tramo', 'anio_escolar'
        ).distinct().order_by('-fecha')),
        version=1,
        timeout=ttl(TTL),
    )


def sesiones_del_centro(centro, anio_escolar):
    if not anio_escolar:
        return []
    clave = f'entrenamiento_sesiones:{centro.id}:{anio_escolar.id}:{_version_entrenamiento(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(SesionEntrenamiento.objects.filter(
            anio_escolar=anio_escolar,
            estudiante__inscripciones__anio_escolar=anio_escolar,
        ).select_related(
            'estudiante', 'unidad', 'unidad__tramo'
        ).distinct().order_by('-fecha_inicio')),
        version=1,
        timeout=ttl(TTL),
    )


def metricas_del_centro(centro, anio_escolar):
    if not anio_escolar:
        return []
    clave = f'entrenamiento_metricas:{centro.id}:{anio_escolar.id}:{_version_entrenamiento(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(MetricaCognitiva.objects.filter(
            anio_escolar=anio_escolar,
        ).select_related(
            'estudiante', 'periodo', 'tramo'
        ).order_by('-fecha_corte')),
        version=1,
        timeout=ttl(TTL),
    )


def planes_refuerzo_del_centro(centro, anio_escolar):
    if not anio_escolar:
        return []
    clave = f'entrenamiento_planes:{centro.id}:{anio_escolar.id}:{_version_entrenamiento(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(PlanRefuerzo.objects.filter(
            anio_escolar=anio_escolar,
        ).select_related(
            'estudiante', 'unidad', 'unidad__tramo'
        ).order_by('-fecha_generado')),
        version=1,
        timeout=ttl(TTL),
    )


def metricas_dashboard(centro, anio_escolar):
    if not anio_escolar:
        return {'total_diagnosticos': 0, 'total_sesiones': 0, 'sesiones_completadas': 0,
                'total_planes': 0, 'planes_activos': 0, 'ipd_promedio': 0}
    clave = f'entrenamiento_dashboard:{centro.id}:{anio_escolar.id}:{_version_entrenamiento(centro.id)}'

    def _calcular():
        diags = DiagnosticoCognitivo.objects.filter(
            anio_escolar=anio_escolar,
            estudiante__inscripciones__anio_escolar=anio_escolar,
        ).distinct()
        sesiones_qs = SesionEntrenamiento.objects.filter(
            anio_escolar=anio_escolar,
            estudiante__inscripciones__anio_escolar=anio_escolar,
        ).distinct()
        planes_qs = PlanRefuerzo.objects.filter(anio_escolar=anio_escolar)

        ipd = sesiones_qs.filter(
            ipd__isnull=False, estado='completada'
        ).aggregate(prom=Coalesce(Avg('ipd'), 0, output_field=DecimalField()))['prom']

        return {
            'total_diagnosticos': diags.count(),
            'total_sesiones': sesiones_qs.count(),
            'sesiones_completadas': sesiones_qs.filter(estado='completada').count(),
            'total_planes': planes_qs.count(),
            'planes_activos': planes_qs.filter(estado='activo').count(),
            'ipd_promedio': round(float(ipd), 2),
        }

    return obtener_o_generar(clave, _calcular, version=1, timeout=ttl('CACHE_TTL_CORTO'))
