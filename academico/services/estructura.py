"""Caché de catálogos de estructura académica (dominio `estructura:{centro}`).

Los listados de catálogo (nivel, grado, seccion, area, asignatura,
competencia, periodo, docentemateria, anio_escolar, franja y horario) se
consultan en cada request. Aquí se cachean las listas base por centro y
las vistas filtran/paginan en memoria.

Estrategia idéntica a caja/facturación/nómina: cuando cambia cualquiera de
estos modelos (o su relación con el año escolar) se incrementa la versión
del dominio y las claves viejas quedan huérfanas.
"""

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from core.models import AnioEscolar

from academico.models import (
    AreaCurricular,
    Asignatura,
    Competencia,
    DocenteMateria,
    FranjaHoraria,
    Grado,
    GradoAsignatura,
    HorarioClase,
    Nivel,
    Periodo,
    PeriodoAnio,
    Seccion,
)

TTL_ESTRUCTURA = 'CACHE_TTL_LARGO'


def invalidar_estructura(centro_id):
    """Invalida todos los catálogos de estructura de un centro."""
    invalidar_dominio(f'estructura:{centro_id}')


def _version(centro_id):
    return obtener_version(f'estructura:{centro_id}')


def _cache(clave, generador, centro_id):
    return obtener_o_generar(
        clave,
        generador,
        version=_version(centro_id),
        timeout=ttl(TTL_ESTRUCTURA),
    )


def niveles(centro):
    return _cache(
        f'estructura_niveles:{centro.id}',
        lambda: list(Nivel.objects.filter(centro=centro).order_by('nombre')),
        centro.id,
    )


def grados(centro):
    return _cache(
        f'estructura_grados:{centro.id}',
        lambda: list(
            Grado.objects.filter(nivel__centro=centro)
            .select_related('nivel')
            .order_by('nivel__nombre', 'orden', 'nombre')
        ),
        centro.id,
    )


def secciones(centro):
    return _cache(
        f'estructura_secciones:{centro.id}',
        lambda: list(
            Seccion.objects.filter(centro=centro)
            .prefetch_related('grados')
            .order_by('nombre')
        ),
        centro.id,
    )


def areas(centro):
    return _cache(
        f'estructura_areas:{centro.id}',
        lambda: list(
            AreaCurricular.objects.filter(centro=centro).order_by('nombre')
        ),
        centro.id,
    )


def asignaturas(centro):
    return _cache(
        f'estructura_asignaturas:{centro.id}',
        lambda: list(
            Asignatura.objects.filter(centro=centro)
            .select_related('area')
            .order_by('area__nombre', 'nombre')
        ),
        centro.id,
    )


def grado_asignaturas(centro):
    return _cache(
        f'estructura_grado_asignaturas:{centro.id}',
        lambda: list(
            GradoAsignatura.objects.filter(
                grado__nivel__centro=centro,
                asignatura__centro=centro,
            )
            .select_related('grado', 'grado__nivel', 'asignatura')
            .order_by('grado__nivel__nombre', 'grado__nombre', 'asignatura__nombre')
        ),
        centro.id,
    )


def competencias(centro):
    return _cache(
        f'estructura_competencias:{centro.id}',
        lambda: list(
            Competencia.objects.filter(nivel__centro=centro)
            .select_related('nivel')
            .order_by('nivel', 'orden', 'nombre')
        ),
        centro.id,
    )


def periodos(centro):
    return _cache(
        f'estructura_periodos:{centro.id}',
        lambda: list(
            Periodo.objects.filter(centro=centro).order_by('orden', 'nombre')
        ),
        centro.id,
    )


def docentes_materia(centro):
    return _cache(
        f'estructura_docentemateria:{centro.id}',
        lambda: list(
            DocenteMateria.objects.filter(docente__centro=centro)
            .select_related(
                'docente',
                'asignatura',
                'grado',
                'seccion',
                'anio_escolar',
            )
            .order_by(
                '-anio_escolar__fecha_inicio',
                'grado__nombre',
                'asignatura__nombre',
            )
        ),
        centro.id,
    )


def anios_escolares(centro):
    return _cache(
        f'estructura_anios:{centro.id}',
        lambda: list(
            AnioEscolar.objects.filter(centro=centro).order_by('-fecha_inicio')
        ),
        centro.id,
    )


def franjas(centro):
    return _cache(
        f'estructura_franjas:{centro.id}',
        lambda: list(
            FranjaHoraria.objects.filter(centro=centro).order_by(
                'orden', 'hora_inicio'
            )
        ),
        centro.id,
    )


def horario_clases(centro):
    return _cache(
        f'estructura_horario_clases:{centro.id}',
        lambda: list(
            HorarioClase.objects.filter(asignacion__docente__centro=centro)
            .select_related(
                'asignacion',
                'asignacion__docente',
                'asignacion__asignatura',
                'asignacion__grado',
                'asignacion__seccion',
                'asignacion__anio_escolar',
                'franja',
            )
            .order_by('dia_semana', 'franja__orden')
        ),
        centro.id,
    )


def horario_clases_por_filtro(centro, grado, seccion, anio):
    """HorarioClase de una sección/grado/año concreto (matriz del horario)."""
    clave = (
        f'estructura_horario_matriz:{centro.id}:'
        f'{grado.id}:{seccion.id}:{anio.id}'
    )
    return _cache(
        clave,
        lambda: list(
            HorarioClase.objects.filter(
                asignacion__grado=grado,
                asignacion__seccion=seccion,
                asignacion__anio_escolar=anio,
                asignacion__docente__centro=centro,
            ).select_related(
                'asignacion',
                'asignacion__docente',
                'asignacion__asignatura',
                'franja',
            )
        ),
        centro.id,
    )


def estados_periodo_anio(anio):
    """Estados (PeriodoAnio) de un año escolar concreto."""
    return _cache(
        f'estructura_periodos_estados:{anio.id}',
        lambda: list(
            PeriodoAnio.objects.filter(anio_escolar=anio).select_related('periodo')
        ),
        anio.centro_id,
    )


def matriz_periodos(centro):
    """Todos los PeriodoAnio del centro (matriz período ↔ año escolar)."""
    return _cache(
        f'estructura_periodos_matriz:{centro.id}',
        lambda: list(
            PeriodoAnio.objects.filter(anio_escolar__centro=centro)
            .select_related('periodo', 'anio_escolar')
            .order_by('anio_escolar__fecha_inicio', 'periodo__orden')
        ),
        centro.id,
    )
