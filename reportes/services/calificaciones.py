"""Servicios de calificaciones para los reportes (planilla y boleta del período).

Todo calcula solo sobre calificaciones ya registradas en la base: nunca
escribe. La lógica de promedios coincide con el motor oficial de boletines
(administracion.services.boletin): una asignatura equivale al promedio de las
notas de sus competencias en el período.
"""

from collections import defaultdict

from administracion.services.boletin import redondear
from academico.models import Calificacion, Competencia, DocenteMateria, GradoAsignatura


def _asignaturas_planilla(grado, seccion, anio):
    """Asignaturas del grado/sección en el año, a partir de la carga real.

    Si el grado/sección no tiene asignaciones cargadas, cae al catálogo de
    asignaturas del grado (GradoAsignatura).
    """
    mapa = {}
    qs = (
        DocenteMateria.objects
        .filter(grado=grado, seccion=seccion, anio_escolar=anio)
        .select_related('asignatura')
    )
    for dm in qs:
        mapa.setdefault(dm.asignatura_id, dm.asignatura)

    if not mapa:
        for ga in (
            GradoAsignatura.objects
            .filter(grado=grado)
            .select_related('asignatura')
        ):
            mapa.setdefault(ga.asignatura_id, ga.asignatura)

    return [
        asignatura
        for _, asignatura in sorted(mapa.items(), key=lambda kv: kv[1].nombre.lower())
    ]


def _asignar_estado(promedio, nota_minima):
    """Clasifica a un estudiante frente a la nota mínima en un período."""
    if promedio is None:
        return 'sin_notas'
    if nota_minima is None:
        return 'pendiente'
    return 'aprobado' if promedio >= nota_minima else 'reprobado'


def planilla_calificaciones(centro, anio, grado, seccion, periodo, inscripciones=None):
    """Notas por estudiante y asignatura en un período dado.

    filas: {inscripcion, notas, promedio_general, estado} (estado puede ser
           sin_notas / pendiente / aprobado / reprobado).
    Devuelve también las columnas de asignaturas, el promedio del grupo por
    asignatura y la nota mínima efectiva del nivel.
    """
    if inscripciones is None:
        from estudiantes.models import Inscripcion

        inscripciones = list(
            Inscripcion.objects
            .filter(centro=centro, anio_escolar=anio, grado=grado, seccion=seccion)
            .select_related('estudiante', 'grado', 'seccion', 'anio_escolar')
            .order_by(
                'estudiante__primer_apellido',
                'estudiante__primer_nombre',
            )
        )

    asignaturas = _asignaturas_planilla(grado, seccion, anio)

    from core.models import ConfiguracionCentro

    configuracion = ConfiguracionCentro.objects.filter(centro=centro).first()
    nota_minima = grado.nivel.nota_minima(configuracion) if grado.nivel_id else None

    por_inscripcion = defaultdict(list)
    insc_ids = [i.id for i in inscripciones]
    if insc_ids:
        for c in (
            Calificacion.objects
            .filter(inscripcion_id__in=insc_ids, periodo=periodo)
            .select_related('asignatura')
        ):
            por_inscripcion[c.inscripcion_id].append(c)

    suma_por_asig = defaultdict(float)
    n_por_asig = defaultdict(int)

    filas = []
    for inscripcion in inscripciones:
        acumulado = defaultdict(list)
        for c in por_inscripcion.get(inscripcion.id, []):
            if c.nota is not None:
                acumulado[c.asignatura_id].append(float(c.nota))

        notas = {}
        for asignatura in asignaturas:
            valores = acumulado.get(asignatura.id, [])
            promedio = sum(valores) / len(valores) if valores else None
            notas[asignatura.id] = redondear(promedio) if promedio is not None else None
            if notas[asignatura.id] is not None:
                suma_por_asig[asignatura.id] += notas[asignatura.id]
                n_por_asig[asignatura.id] += 1

        con_nota = [n for n in notas.values() if n is not None]
        promedio_general = (
            redondear(sum(con_nota) / len(con_nota)) if con_nota else None
        )

        filas.append({
            'inscripcion': inscripcion,
            'notas': notas,
            'promedio_general': promedio_general,
            'estado': _asignar_estado(promedio_general, nota_minima),
        })

    promedios_por_asignatura = {
        a.id: redondear(suma_por_asig[a.id] / n_por_asig[a.id])
        for a in asignaturas
        if n_por_asig[a.id]
    }

    return {
        'asignaturas': asignaturas,
        'filas': filas,
        'promedios_por_asignatura': promedios_por_asignatura,
        'nota_minima': nota_minima,
    }


def boleta_periodo(inscripcion, anio, periodo, centro):
    """Boleta de un estudiante para un período: competencia por competencia.

    Reutiliza el catálogo de competencias del nivel (igual que el boletín
    oficial). El promedio del área en el período es el promedio de las notas
    de sus competencias con calificación registrada.
    """
    grado = inscripcion.grado
    seccion = inscripcion.seccion

    from core.models import ConfiguracionCentro

    configuracion = ConfiguracionCentro.objects.filter(centro=centro).first()
    nota_minima = grado.nivel.nota_minima(configuracion) if grado.nivel_id else None

    competencias_catalogo = list(
        Competencia.objects
        .filter(nivel=grado.nivel, activo=True)
        .order_by('orden', 'nombre')
    )

    calificaciones = list(
        Calificacion.objects
        .filter(inscripcion=inscripcion, periodo=periodo)
        .select_related('asignatura', 'competencia')
    )

    por_asignatura = defaultdict(dict)
    for c in calificaciones:
        if c.nota is not None:
            por_asignatura[c.asignatura_id][c.competencia_id] = float(c.nota)

    detalle = []
    for asignatura in _asignaturas_planilla(grado, seccion, anio):
        notas_competencias = por_asignatura.get(asignatura.id, {})

        competencias = [
            {
                'nombre': competencia.nombre,
                'nota': notas_competencias.get(competencia.id),
            }
            for competencia in competencias_catalogo
        ]

        con_nota = [c['nota'] for c in competencias if c['nota'] is not None]
        promedio = redondear(sum(con_nota) / len(con_nota)) if con_nota else None

        detalle.append({
            'asignatura': asignatura,
            'competencias': competencias,
            'promedio': promedio,
            'estado': _asignar_estado(promedio, nota_minima),
        })

    con_nota = [d['promedio'] for d in detalle if d['promedio'] is not None]
    promedio_general = redondear(sum(con_nota) / len(con_nota)) if con_nota else None
    estado_general = _asignar_estado(promedio_general, nota_minima)

    return {
        'centro': centro,
        'anio': anio,
        'periodo': periodo,
        'inscripcion': inscripcion,
        'estudiante': inscripcion.estudiante,
        'grado': grado,
        'seccion': seccion,
        'detalle': detalle,
        'promedio_general': promedio_general,
        'estado_general': estado_general,
        'nota_minima': nota_minima,
    }