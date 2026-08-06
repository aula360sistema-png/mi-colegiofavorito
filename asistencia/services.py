from datetime import date, timedelta

from .models import AsistenciaEstudiante, DiaNoDocencia


def _fechas_no_docencia(anio_escolar):
    """Conjunto de fechas marcadas como no docencia para el año escolar."""
    return set(
        DiaNoDocencia.objects.filter(
            anio_escolar=anio_escolar
        ).values_list('fecha', flat=True)
    )


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


def calcular_promedio_inscripcion(inscripcion, hasta=None):
    """Porcentaje de asistencia de un estudiante hasta una fecha.

    Solo se toman en cuenta los días lectivos transcurridos desde su
    inscripción. Los días de no docencia, fines de semana y feriados
    quedan excluidos del cálculo.
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

    registros = {
        a.fecha: a.estado
        for a in AsistenciaEstudiante.objects.filter(
            inscripcion=inscripcion,
            fecha__in=fechas
        )
    }

    asistencias = sum(
        1
        for f in fechas
        if registros.get(f) in AsistenciaEstudiante.ESTADOS_ASISTIDO
    )

    ausencias = sum(
        1
        for f in fechas
        if registros.get(f) == 'ausente'
    )

    porcentaje = (asistencias / len(fechas)) * 100

    return {
        'dias_lectivos': len(fechas),
        'asistencias': asistencias,
        'ausencias': ausencias,
        'porcentaje': round(porcentaje, 2),
    }


def resumen_por_inscripciones(inscripciones, hasta=None):
    """Resumen de asistencia para varias inscripciones."""
    return [
        {
            'inscripcion': inscripcion,
            **calcular_promedio_inscripcion(inscripcion, hasta=hasta),
        }
        for inscripcion in inscripciones
    ]
