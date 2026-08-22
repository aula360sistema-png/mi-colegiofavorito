"""Caché de listados y panel del tutor (dominio `tutores:{centro}`).

Estrategia idéntica a caja/nómina: cuando cambia Tutor, su vínculo
estudiantes (M2M), Inscripcion o Estudiante se incrementa la versión del
dominio y las claves viejas quedan huérfanas.
"""

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from tutores.models import Tutor

TTL_TUTORES = 'CACHE_TTL_MEDIO'


def invalidar_tutores_centro(centro_id):
    """Invalida el listado y los paneles de tutores de un centro."""
    invalidar_dominio(f'tutores:{centro_id}')


def _version_tutores(centro_id):
    return obtener_version(f'tutores:{centro_id}')


def tutores_del_centro(centro):
    """Todos los tutores del centro con sus estudiantes (cacheados).

    La vista filtra en memoria (búsqueda) y pagina sobre la lista base.
    """
    clave = f'tutores_lista:{centro.id}:{_version_tutores(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(
            Tutor.objects.filter(centro=centro)
            .prefetch_related('estudiantes')
            .order_by('primer_apellido', 'primer_nombre')
        ),
        version=1,
        timeout=ttl(TTL_TUTORES),
    )


def datos_inicio_tutor(tutor):
    """Estudiantes del tutor con su inscripción activa (cacheado).

    El panel del tutor consulta por estudiante la inscripción del año
    activo; aquí se prefetchea una sola vez por dominio.
    """
    clave = f'tutor_inicio:{tutor.id}:{_version_tutores(tutor.centro_id)}'
    return obtener_o_generar(
        clave,
        lambda: _datos_inicio_tutor_sql(tutor),
        version=1,
        timeout=ttl(TTL_TUTORES),
    )


def _datos_inicio_tutor_sql(tutor):
    from django.db.models import Prefetch

    from estudiantes.models import Inscripcion

    estudiantes = list(
        tutor.estudiantes
        .select_related('centro')
        .prefetch_related(
            Prefetch(
                'inscripciones',
                queryset=(
                    Inscripcion.objects
                    .filter(anio_escolar__activo=True)
                    .select_related('grado', 'seccion', 'anio_escolar')
                ),
                to_attr='inscripcion_activa',
            )
        )
        .order_by('primer_apellido', 'primer_nombre')
    )

    return [
        {
            'estudiante': e,
            'inscripcion_actual': (getattr(e, 'inscripcion_activa', None) or [None])[0],
        }
        for e in estudiantes
    ]
