"""Lógica de "quién debe qué" para la recuperación y el extraordinario.

Concentre la decisión de qué asignaturas presenta cada estudiante en su
recuperación/completivo usando la nota mínima de aprobación del NIVEL
(en vez de la general del centro), con fallback al valor del centro si el
nivel no tiene uno específico (Ordenanza 04-2023: 65 Primaria / 70 Secundaria).

También garantiza que el docente responsable se muestre una sola vez por
asignatura, deduplicando las asignaciones de DocenteMateria.
"""

from collections import defaultdict

from academico.models import DocenteMateria
from administracion.services.boletin import construir_boletin_estudiante


def nota_minima_estudiante(inscripcion, configuracion):
    """Nota mínima efectiva del estudiante según el nivel, con fallback al centro."""
    nivel = inscripcion.grado.nivel
    if nivel is None:
        if configuracion is not None and configuracion.nota_minima_aprobacion is not None:
            return float(configuracion.nota_minima_aprobacion)
        return None
    return nivel.nota_minima(configuracion)


def asignaturas_reprobadas_con_docente(inscripcion, centro, anio, nota_minima):
    """Asignaturas por debajo del mínimo, con su docente responsable único.

    Devuelve lista de dicts con: asignatura_id, asignatura, nota (pf) y
    docente (o None). No repite división de competencias ni docentes.
    """
    boletin = construir_boletin_estudiante(inscripcion, centro, anio)

    reprobadas = [
        a for a in boletin['asignaturas']
        if a.get('pf') is not None and a['pf'] < nota_minima
    ]
    if not reprobadas:
        return []

    # Mapa asignatura -> docente (primera asignación determinista).
    asignaciones = (
        DocenteMateria.objects
        .filter(
            grado=inscripcion.grado,
            seccion=inscripcion.seccion,
            anio_escolar=anio,
            asignatura_id__in=[a['asignatura_id'] for a in reprobadas],
        )
        .select_related('asignatura', 'docente')
        .order_by('asignatura_id', 'docente__primer_apellido', 'id')
    )

    docente_por_asignatura = {}
    for asig in asignaciones:
        if asig.asignatura_id in docente_por_asignatura:
            continue
        docente_por_asignatura[asig.asignatura_id] = asig.docente

    detalle = []
    for a in reprobadas:
        detalle.append({
            'asignatura_id': a['asignatura_id'],
            'asignatura': a['asignatura'],
            'nota': a['pf'],
            'docente': docente_por_asignatura.get(a['asignatura_id']),
        })

    return detalle
