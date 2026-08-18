from datetime import date, timedelta

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from .models import AsistenciaEstudiante, DiaNoDocencia

TTL_ASISTENCIA = 'CACHE_TTL_MEDIO'


# =========================================================
# CACHÉ DE AGREGADOS DE ASISTENCIA
# =========================================================
#
# Estrategia idéntica a caja/nómina: dominio de invalidación
# `asistencia:{centro}`. Cuando cambia AsistenciaEstudiante o
# DiaNoDocencia se incrementa la versión y todas las claves del
# centro quedan invalidadas de forma inmediata.


def invalidar_asistencia_centro(centro_id):
    """Invalida resúmenes y estado de asistencia de un centro."""
    invalidar_dominio(f'asistencia:{centro_id}')


def _version_asistencia(centro_id):
    return obtener_version(f'asistencia:{centro_id}')


def _fechas_no_docencia(anio_escolar):
    """Conjunto de fechas marcadas como no docencia para el año escolar
    (cacheado por dominio del centro)."""
    clave = (
        f'asistencia_no_docencia:{anio_escolar.id}:'
        f'{_version_asistencia(anio_escolar.centro_id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: set(
            DiaNoDocencia.objects.filter(
                anio_escolar=anio_escolar
            ).values_list('fecha', flat=True)
        ),
        version=1,
        timeout=ttl(TTL_ASISTENCIA),
    )


def _registros_asistencia_anio(anio_escolar):
    """Mapa {inscripcion_id: {fecha: estado}} de todo el año (cacheado).

    Reemplaza las N consultas por inscripción del resumen por una sola
    consulta base; las vistas agregan en memoria.
    """
    clave = (
        f'asistencia_registros:{anio_escolar.id}:'
        f'{_version_asistencia(anio_escolar.centro_id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _registros_asistencia_anio_sql(anio_escolar),
        version=1,
        timeout=ttl(TTL_ASISTENCIA),
    )


def _registros_asistencia_anio_sql(anio_escolar):
    registros = {}
    pares = AsistenciaEstudiante.objects.filter(
        inscripcion__anio_escolar=anio_escolar
    ).values_list('inscripcion_id', 'fecha', 'estado')

    for inscripcion_id, fecha, estado in pares:
        registros.setdefault(inscripcion_id, {})[fecha] = estado

    return registros


def registros_del_dia(anio_escolar, fecha):
    """{inscripcion_id: estado} registrado en una fecha concreta (cacheado).

    Usado por el recordatorio del docente para saber si ya pasó lista hoy
    sin lanzar una consulta por sección.
    """
    return {
        inscripcion_id: mapa.get(fecha)
        for inscripcion_id, mapa in _registros_asistencia_anio(anio_escolar).items()
        if fecha in mapa
    }


def es_dia_lectivo(anio_escolar, fecha):
    """¿El día cuenta para asistencia?
    - Debe estar dentro del rango del año escolar activo.
    - Solo de lunes a viernes.
    - No debe ser un día de no docencia.
    """
    if not (anio_escolar.fecha_inicio <= fecha <= anio_escolar.fecha_fin):
        return False

    if fecha.weekday() >= 5:
        return False

    if fecha in _fechas_no_docencia(anio_escolar):
        return False

    return True


def dias_lectivos(anio_escolar, hasta=None):
    """Lista de fechas lectivas del año escolar (opcionalmente hasta una fecha)."""
    hasta = hasta or date.today()

    if hasta > anio_escolar.fecha_fin:
        hasta = anio_escolar.fecha_fin

    if hasta < anio_escolar.fecha_inicio:
        return []

    no_docencia = _fechas_no_docencia(anio_escolar)

    dias = []
    fecha = anio_escolar.fecha_inicio

    while fecha <= hasta:
        if fecha.weekday() < 5 and fecha not in no_docencia:
            dias.append(fecha)
        fecha += timedelta(days=1)

    return dias


def calcular_promedio_inscripcion(inscripcion, hasta=None, registros=None):
    """Porcentaje de asistencia de un estudiante hasta una fecha.

    Solo se toman en cuenta los días lectivos transcurridos desde su
    inscripción. Los días de no docencia, fines de semana y feriados
    quedan excluidos del cálculo.

    Si se pasa `registros` (mapa del año, ver `_registros_asistencia_anio`)
    no se consulta la BD por inscripción.
    """
    hasta = hasta or date.today()

    anio = inscripcion.anio_escolar

    inicio = max(anio.fecha_inicio, inscripcion.fecha)

    if hasta < inicio:
        return {
            'dias_lectivos': 0,
            'asistencias': 0,
            'ausencias': 0,
            'porcentaje': None,
        }

    fechas = dias_lectivos(anio, hasta=hasta)
    fechas = [f for f in fechas if f >= inicio]

    if not fechas:
        return {
            'dias_lectivos': 0,
            'asistencias': 0,
            'ausencias': 0,
            'porcentaje': None,
        }

    if registros is None:
        registros = _registros_asistencia_anio(anio)

    mapa = registros.get(inscripcion.id, {})

    asistencias = sum(
        1
        for f in fechas
        if mapa.get(f) in AsistenciaEstudiante.ESTADOS_ASISTIDO
    )

    ausencias = sum(
        1
        for f in fechas
        if mapa.get(f) == 'ausente'
    )

    porcentaje = (asistencias / len(fechas)) * 100

    return {
        'dias_lectivos': len(fechas),
        'asistencias': asistencias,
        'ausencias': ausencias,
        'porcentaje': round(porcentaje, 2),
    }


def resumen_por_inscripciones(inscripciones, hasta=None):
    """Resumen de asistencia para varias inscripciones (con caché)."""
    if not inscripciones:
        return []

    mapas = {}
    for inscripcion in inscripciones:
        anio = inscripcion.anio_escolar
        mapas.setdefault(anio.id, _registros_asistencia_anio(anio))

    return [
        {
            'inscripcion': inscripcion,
            **calcular_promedio_inscripcion(
                inscripcion,
                hasta=hasta,
                registros=mapas[inscripcion.anio_escolar_id],
            ),
        }
        for inscripcion in inscripciones
    ]
