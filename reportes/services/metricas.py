"""Agregados del tablero de reportes (cacheados por centro)."""

from django.db.models import Count

from core.cache_utils import (
    obtener_o_generar,
    obtener_version,
    ttl,
)
from core.utils.anio import obtener_anio_activo
from estudiantes.models import Estudiante, Inscripcion


def obtener_metricas_reportes(centro):
    clave = (
        f'reportes:{centro.id}:'
        f'{obtener_version(f"estructura:{centro.id}")}:'
        f'{obtener_version(f"estudiantes:{centro.id}")}'
    )
    return obtener_o_generar(
        clave,
        lambda: _obtener_metricas_reportes_sql(centro),
        version=1,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


def _obtener_metricas_reportes_sql(centro):
    anio_actual = obtener_anio_activo(centro)

    matricula_por_grado = list(
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('grado__nombre', 'seccion__nombre')
        .annotate(total=Count('id'))
        .order_by('grado__orden', 'seccion__nombre')
        if anio_actual else []
    )

    matricula_por_anio = list(
        Inscripcion.objects
        .filter(centro=centro)
        .values('anio_escolar__nombre')
        .annotate(total=Count('id'))
        .order_by('-anio_escolar__fecha_inicio')
    )

    estudiantes_por_estado = list(
        Estudiante.objects
        .filter(centro=centro)
        .values('estado')
        .annotate(total=Count('id'))
    )

    estados_academicos = list(
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('estado_final')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    total_matricula_activa = sum(r['total'] for r in matricula_por_grado)
    total_estudiantes = Estudiante.objects.filter(centro=centro).count()
    total_estados_academicos = sum(r['total'] for r in estados_academicos)

    return {
        'anio_actual': anio_actual,
        'matricula_por_grado': matricula_por_grado,
        'matricula_por_anio': matricula_por_anio,
        'estudiantes_por_estado': estudiantes_por_estado,
        'estados_academicos': estados_academicos,
        'total_matricula_activa': total_matricula_activa,
        'total_estudiantes': total_estudiantes,
        'total_estados_academicos': total_estados_academicos,
    }