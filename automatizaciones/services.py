from datetime import timedelta

from django.utils import timezone

from academico.models import Calificacion, PeriodoAnio
from asistencia.models import AsistenciaEstudiante
from caja.models import ConceptoPago, Pago
from estudiantes.models import Estudiante, Inscripcion

NOTA_MINIMA = 70
CONSECUTIVAS_INASISTENCIAS = 3
DIAS_SIN_PAGO = 30

ESTADOS_INSCRIPCION_ACTIVA = ('pendiente', 'recuperacion', 'promocion_condicional')


def obtener_anio_activo(centro):
    from core.utils.anio import obtener_anio_activo as _obtener
    return _obtener(centro)


def _tutor_ids(estudiante, centro):
    return list(
        estudiante.tutores
        .filter(centro=centro, estado='activo')
        .values_list('pk', flat=True)
    )


def _seccion_label(inscripcion):
    return f'{inscripcion.grado.nombre} · {inscripcion.seccion.nombre}'


def _inscripciones_activas(centro, anio_escolar):
    return (
        Inscripcion.objects
        .filter(
            centro=centro,
            anio_escolar=anio_escolar,
            estado_final__in=ESTADOS_INSCRIPCION_ACTIVA,
        )
        .select_related('estudiante', 'grado', 'seccion')
    )


def detectar_inasistencias(centro, anio_escolar, minimo=CONSECUTIVAS_INASISTENCIAS):
    """Estudiantes con N ausencias consecutivas en sus últimos registros."""
    inscripciones = _inscripciones_activas(centro, anio_escolar)
    if not inscripciones.exists():
        return []

    registros = (
        AsistenciaEstudiante.objects
        .filter(inscripcion__in=inscripciones)
        .order_by('inscripcion_id', '-fecha', '-id')
        .values_list('inscripcion_id', 'estado')
    )

    estados_por_inscripcion = {}
    for insc_id, estado in registros:
        estados_por_inscripcion.setdefault(insc_id, []).append(estado)

    items = []
    for inscripcion in inscripciones:
        estados = estados_por_inscripcion.get(inscripcion.pk, [])
        consecutivas = 0
        for estado in estados:
            if estado != 'ausente':
                break
            consecutivas += 1
        if consecutivas >= minimo:
            items.append({
                'estudiante': inscripcion.estudiante,
                'seccion': _seccion_label(inscripcion),
                'detalle': f'{consecutivas} ausencias consecutivas registradas',
                'consecutivas': consecutivas,
                'tutor_ids': _tutor_ids(inscripcion.estudiante, centro),
            })
    return items


def detectar_notas_rojas(centro, anio_escolar, nota_minima=NOTA_MINIMA):
    """Estudiantes con materias cuya nota promedio del período baja del mínimo."""
    periodo_anio = (
        PeriodoAnio.objects
        .filter(anio_escolar=anio_escolar, activo=True, cerrado=False)
        .select_related('periodo')
        .order_by('periodo__orden')
        .last()
    )
    if periodo_anio is None:
        return []

    calificaciones = (
        Calificacion.objects
        .filter(
            inscripcion__centro=centro,
            inscripcion__anio_escolar=anio_escolar,
            periodo=periodo_anio.periodo,
        )
        .select_related(
            'asignatura',
            'inscripcion',
            'inscripcion__estudiante',
            'inscripcion__grado',
            'inscripcion__seccion',
        )
    )

    acumulado = {}
    for calificacion in calificaciones:
        clave = (calificacion.inscripcion_id, calificacion.asignatura_id)
        if clave not in acumulado:
            acumulado[clave] = [calificacion.asignatura.nombre, []]
        acumulado[clave][1].append(float(calificacion.nota))

    rojas_por_inscripcion = {}
    for (insc_id, _), (nombre, notas) in acumulado.items():
        promedio = sum(notas) / len(notas)
        if promedio < nota_minima:
            rojas_por_inscripcion.setdefault(insc_id, []).append(
                (nombre, round(promedio, 2))
            )

    if not rojas_por_inscripcion:
        return []

    inscripciones = (
        Inscripcion.objects
        .filter(pk__in=list(rojas_por_inscripcion))
        .select_related('estudiante', 'grado', 'seccion')
    )

    items = []
    for inscripcion in inscripciones:
        rojas = rojas_por_inscripcion[inscripcion.pk]
        items.append({
            'estudiante': inscripcion.estudiante,
            'seccion': _seccion_label(inscripcion),
            'detalle': ' · '.join(f'{nombre} ({promedio})' for nombre, promedio in sorted(rojas)),
            'asignaturas': rojas,
            'periodo': periodo_anio.periodo.nombre,
            'tutor_ids': _tutor_ids(inscripcion.estudiante, centro),
        })
    return items


def detectar_pagos_vencidos(centro, anio_escolar, dias=DIAS_SIN_PAGO):
    """Estudiantes inscritos sin pago recurrente registrado recientemente."""
    conceptos = ConceptoPago.objects.filter(
        centro=centro,
        es_recurrente=True,
        activo=True,
    )
    if not conceptos.exists():
        return []

    limite = timezone.localdate() - timedelta(days=dias)
    inscripciones = _inscripciones_activas(centro, anio_escolar)
    monto_recurrente = sum(float(concepto.monto) for concepto in conceptos)

    items = []
    for inscripcion in inscripciones:
        tuvo_pago = (
            Pago.objects
            .filter(
                estudiante=inscripcion.estudiante,
                concepto__in=conceptos,
                fecha__gte=limite,
            )
            .exists()
        )
        if not tuvo_pago:
            items.append({
                'estudiante': inscripcion.estudiante,
                'seccion': _seccion_label(inscripcion),
                'detalle': (
                    f'Sin pago recurrente en los últimos {dias} días '
                    f'(pendiente ≈ RD$ {monto_recurrente:,.2f})'
                ),
                'deuda': monto_recurrente,
                'tutor_ids': _tutor_ids(inscripcion.estudiante, centro),
            })
    return items


def detectar_cumpleanos(centro, anio_escolar):
    """Estudiantes inscritos que cumplen años hoy."""
    hoy = timezone.localdate()
    inscripciones = (
        _inscripciones_activas(centro, anio_escolar)
        .filter(
            estudiante__estado='activo',
            estudiante__fecha_nacimiento__month=hoy.month,
            estudiante__fecha_nacimiento__day=hoy.day,
        )
    )

    items = []
    for inscripcion in inscripciones:
        nacimiento = inscripcion.estudiante.fecha_nacimiento
        edad = (
            hoy.year - nacimiento.year
            - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        )
        items.append({
            'estudiante': inscripcion.estudiante,
            'seccion': _seccion_label(inscripcion),
            'detalle': f'Cumple {edad} años hoy',
            'edad': edad,
            'tutor_ids': _tutor_ids(inscripcion.estudiante, centro),
        })
    return items


GRUPOS_ALERTA = (
    ('inasistencias', 'Inasistencias consecutivas', 'fa-user-clock', 'amber'),
    ('notas_rojas', 'Notas en rojo', 'fa-graduation-cap', 'rose'),
    ('pagos_vencidos', 'Pagos recurrentes sin registrar', 'fa-money-bill-wave', 'sky'),
    ('cumpleanos', 'Cumpleaños de hoy', 'fa-cake-candles', 'violet'),
)


def generar_tablero(centro, anio_escolar):
    if anio_escolar is None:
        return {'anio': None, 'grupos': []}

    detectores = {
        'inasistencias': detectar_inasistencias,
        'notas_rojas': detectar_notas_rojas,
        'pagos_vencidos': detectar_pagos_vencidos,
        'cumpleanos': detectar_cumpleanos,
    }

    grupos = []
    for clave, titulo, icono, color in GRUPOS_ALERTA:
        items = detectores[clave](centro, anio_escolar)
        grupos.append({
            'clave': clave,
            'titulo': titulo,
            'icono': icono,
            'color': color,
            'total': len(items),
            'items': items,
        })

    return {'anio': anio_escolar, 'grupos': grupos}