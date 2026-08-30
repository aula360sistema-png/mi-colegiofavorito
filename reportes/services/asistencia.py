"""Servicios de consulta de asistencia para los reportes."""

MESES_NOMBRES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def conteo_asistencia(estados):
    """Cuenta los registros de asistencia por estado y su porcentaje."""
    conteo = {'presente': 0, 'tardanza': 0, 'justificado': 0, 'ausente': 0}
    for e in estados:
        if e in conteo:
            conteo[e] += 1
    conteo['asistido'] = (
        conteo['presente'] + conteo['tardanza'] + conteo['justificado']
    )
    conteo['total'] = sum(
        conteo[k] for k in ('presente', 'tardanza', 'justificado', 'ausente')
    )
    conteo['porcentaje'] = (
        round(conteo['asistido'] / conteo['total'] * 100, 1)
        if conteo['total'] else None
    )
    return conteo


def registros_asistencia(inscripciones, anio, mes=None):
    """Registros de asistencia de un grupo de inscripciones en un año."""
    from asistencia.models import AsistenciaEstudiante

    insc_ids = [i.id for i in inscripciones]
    if not insc_ids:
        return []
    qs = AsistenciaEstudiante.objects.filter(
        inscripcion_id__in=insc_ids,
        fecha__range=(anio.fecha_inicio, anio.fecha_fin),
    )
    if mes:
        qs = qs.filter(fecha__month=int(mes))
    return list(qs.select_related())


def resumen_asistencia_estudiante(inscripcion, anio, mes=None):
    """Resumen mensual + detalle diario de asistencia de un estudiante."""
    registros = registros_asistencia([inscripcion], anio, mes)

    meses = []
    for num in range(1, 13):
        estados = [r.estado for r in registros if r.fecha.month == num]
        if estados:
            meses.append({
                'numero': num,
                'nombre': MESES_NOMBRES[num - 1],
                **conteo_asistencia(estados),
            })

    detalle = [
        {
            'fecha': r.fecha,
            'dia': DIAS_SEMANA[r.fecha.weekday()],
            'estado': r.estado,
            'estado_display': r.get_estado_display(),
        }
        for r in registros
    ]

    return {
        'meses': meses,
        'detalle': detalle,
        'totales': conteo_asistencia([r.estado for r in registros]),
        'dias': len(detalle),
    }


def resumen_asistencia_seccion(inscripciones, anio, mes=None):
    """Resumen por estudiante + planilla mensual de un grado/sección."""
    registros = registros_asistencia(inscripciones, anio, mes)

    mapa = {}
    for r in registros:
        mapa.setdefault((r.inscripcion_id, r.fecha), r.estado)

    filas = []
    for i in inscripciones:
        estados = [
            mapa[(i.id, f)]
            for f in sorted(
                {r.fecha for r in registros if r.inscripcion_id == i.id}
            )
        ]
        filas.append({'inscripcion': i, **conteo_asistencia(estados)})

    dias = sorted({r.fecha for r in registros})
    dias_celdas = [
        {
            'fecha': fecha,
            'dia': DIAS_SEMANA[fecha.weekday()],
            'celdas': {i.id: mapa.get((i.id, fecha), '') for i in inscripciones},
        }
        for fecha in dias
    ]

    return {
        'filas': filas,
        'dias': dias,
        'dias_celdas': dias_celdas,
        'totales': conteo_asistencia([r.estado for r in registros]),
        'mes': int(mes) if mes else None,
        'hay_registros': bool(registros),
    }