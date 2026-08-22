from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from estudiantes.models import Estudiante, Inscripcion

TTL_ESTUDIANTES = 'CACHE_TTL_MEDIO'


def invalidar_estudiantes_centro(centro_id):
    """Invalida listas de estudiantes de un centro."""
    invalidar_dominio(f'estudiantes:{centro_id}')


def _version_estudiantes(centro_id):
    return obtener_version(f'estudiantes:{centro_id}')


def estudiantes_del_centro(centro, anio_escolar):
    """Todos los estudiantes del centro con su inscripción actual.

    Se cachea con el dominio `estudiantes:{centro}`. La vista filtra en
    memoria (búsqueda, estado matriculado/sin matrícula).
    """
    clave = (
        f'estudiantes_lista:{centro.id}:'
        f'{anio_escolar.id if anio_escolar else 0}:'
        f'{_version_estudiantes(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _estudiantes_del_centro_sql(centro, anio_escolar),
        version=1,
        timeout=ttl(TTL_ESTUDIANTES),
    )


def _estudiantes_del_centro_sql(centro, anio_escolar):
    from django.db.models import Prefetch

    estudiantes = (
        Estudiante.objects
        .filter(centro=centro)
        .prefetch_related(
            Prefetch(
                'inscripciones',
                queryset=(
                    Inscripcion.objects
                    .filter(anio_escolar=anio_escolar)
                    .select_related('grado', 'seccion', 'anio_escolar')
                ),
                to_attr='inscripcion_actual',
            )
        )
        .order_by('primer_apellido', 'segundo_apellido', 'primer_nombre')
    )
    return list(estudiantes)


def inscripciones_del_centro(centro):
    """Todas las inscripciones del centro (historial), cacheadas por dominio.

    La vista filtra en memoria (estudiante, año, grado, sección, estado).
    """
    clave = f'inscripciones_lista:{centro.id}:{_version_estudiantes(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: _inscripciones_del_centro_sql(centro),
        version=1,
        timeout=ttl(TTL_ESTUDIANTES),
    )


def _inscripciones_del_centro_sql(centro):
    inscripciones = (
        Inscripcion.objects
        .filter(centro=centro)
        .select_related('estudiante', 'grado', 'seccion', 'anio_escolar')
        .order_by(
            '-anio_escolar__fecha_inicio',
            'grado__nombre',
            'seccion__nombre',
            'estudiante__primer_apellido',
        )
    )
    return list(inscripciones)


def observaciones_del_centro(centro):
    """Todas las observaciones de disciplina del centro, cacheadas.

    La vista filtra y agrega en memoria (q, tipo, año, grado, sección y
    resumen por tipo) sobre esta lista base.
    """
    clave = f'observaciones_lista:{centro.id}:{_version_estudiantes(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: _observaciones_del_centro_sql(centro),
        version=1,
        timeout=ttl(TTL_ESTUDIANTES),
    )


def _observaciones_del_centro_sql(centro):
    from django.db.models import Prefetch
    from estudiantes.models import ObservacionEstudiante

    return list(
        ObservacionEstudiante.objects
        .filter(estudiante__centro=centro)
        .select_related('estudiante', 'anio_escolar')
        .prefetch_related(
            Prefetch(
                'estudiante__inscripciones',
                queryset=Inscripcion.objects.filter(centro=centro),
                to_attr='inscripciones_centro',
            )
        )
    )


def solicitudes_del_centro(centro):
    """Solicitudes de certificados del centro, cacheadas.

    La vista filtra en memoria (búsqueda, estado, tipo) sobre esta lista
    base; comparte el dominio `estudiantes:{centro}`.
    """
    clave = f'solicitudes_lista:{centro.id}:{_version_estudiantes(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: _solicitudes_del_centro_sql(centro),
        version=1,
        timeout=ttl(TTL_ESTUDIANTES),
    )


def _solicitudes_del_centro_sql(centro):
    from estudiantes.models import SolicitudCertificado

    return list(
        SolicitudCertificado.objects
        .filter(estudiante__centro=centro)
        .select_related(
            'estudiante',
            'solicitante',
            'aprobado_por',
            'entregado_por',
        )
        .order_by('-created_at')
    )
