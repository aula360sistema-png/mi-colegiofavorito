"""Visibilidad de comunicados para los portales de estudiante y tutor.

Reglas:
  - Solo se muestran comunicados vigentes (publicados y no vencidos).
  - Alcance "todos": lo ve todo el centro.
  - Alcance "seccion": solo los estudiantes inscritos en esa seccion
    durante el ano escolar activo, mas los tutores de esos estudiantes.

El resultado por estudiante/tutor se cachea bajo el dominio
`comunicaciones:{centro}`; las signals invalidan el dominio al crear,
editar o borrar un comunicado.
"""

from django.db.models import Q
from django.utils import timezone

from core.cache_utils import invalidar_dominio, obtener_o_generar, obtener_version, ttl

DOMINIO_POR_CENTRO = 'comunicaciones:{centro_id}'


def dominio_centro(centro_id):
    return DOMINIO_POR_CENTRO.format(centro_id=centro_id)


def _base_vigentes(centro_id):
    """QuerySet base: publicados y aun no vencidos, mejor fijados primero."""
    from comunicaciones.models import Comunicado

    hoy = timezone.localdate()
    return (
        Comunicado.objects
        .filter(centro_id=centro_id)
        .filter(fecha_publicacion__date__lte=hoy)
        .filter(
            Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=hoy)
        )
        .order_by('-fijado', '-fecha_publicacion')
    )


def comunicados_para_estudiante(estudiante):
    """Lista de comunicados visibles para un estudiante (cacheada)."""
    from estudiantes.models import Inscripcion

    centro_id = estudiante.centro_id
    clave = f'comunicados:est:{estudiante.pk}'

    def generador():
        secciones = list(
            Inscripcion.objects
            .filter(
                estudiante=estudiante,
                centro_id=centro_id,
                anio_escolar__activo=True,
            )
            .values_list('seccion_id', flat=True)
        )

        query = _base_vigentes(centro_id).filter(alcance='todos')
        if secciones:
            query = query | _base_vigentes(centro_id).filter(
                alcance='seccion', seccion_id__in=secciones
            )

        return list(query.distinct())

    return _obtener_cache(centro_id, clave, generador)


def comunicados_para_tutor(tutor):
    """Lista de comunicados visibles para un tutor segun sus hijos (cacheada)."""
    from estudiantes.models import Inscripcion

    centro_id = tutor.centro_id
    clave = f'comunicados:tut:{tutor.pk}'

    def generador():
        secciones = list(
            Inscripcion.objects
            .filter(
                anio_escolar__activo=True,
                centro_id=centro_id,
                estudiante__in=tutor.estudiantes.all(),
            )
            .values_list('seccion_id', flat=True)
        )

        query = _base_vigentes(centro_id).filter(alcance='todos')
        if secciones:
            query = query | _base_vigentes(centro_id).filter(
                alcance='seccion', seccion_id__in=secciones
            )

        return list(query.distinct())

    return _obtener_cache(centro_id, clave, generador)


def ultimos_comunicados(objeto, cantidad=3, es_tutor=False):
    """Recorte de los N comunicados mas recientes para un portal."""
    lista = (
        comunicados_para_tutor(objeto) if es_tutor
        else comunicados_para_estudiante(objeto)
    )
    return lista[:cantidad]


# ---------------------------------------------------------------------------
# Cache interno
# ---------------------------------------------------------------------------

def _obtener_cache(centro_id, clave, generador):
    version = obtener_version(dominio_centro(centro_id))
    return obtener_o_generar(
        clave,
        generador,
        version=version,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


def invalidar_comunicados(centro_id):
    """Invalida el dominio de comunicados de un centro."""
    invalidar_dominio(dominio_centro(centro_id))

