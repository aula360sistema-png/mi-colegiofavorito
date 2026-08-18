import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from academico.models import Calificacion, DocenteMateria, Periodo
from core.models import ConfiguracionCentro
from estudiantes.models import Inscripcion
from core.cache_utils import (
    obtener_o_generar,
    obtener_version,
    invalidar_dominio,
    ttl,
)

REDONDEAR_TTL = 'CACHE_TTL_MEDIO'


def invalidar_kardex_estudiante(estudiante_id):
    """Invalida el kardex y record de notas de un estudiante."""
    invalidar_dominio(f'estudiante:{estudiante_id}')


def invalidar_kardex_estructura(centro_id):
    """Invalida el kardex de todo un centro cuando cambia su estructura
    (períodos, asignaciones docente-materia, grados)."""
    invalidar_dominio(f'estructura:{centro_id}')


def _clave_kardex(estudiante_id, centro_id):
    return (
        f'kardex:{estudiante_id}:'
        f'{obtener_version(f"estudiante:{estudiante_id}")}:'
        f'{obtener_version(f"estructura:{centro_id}")}'
    )


def redondear(valor):
    return float(
        Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _nota_minima_aprobacion(centro):
    return obtener_o_generar(
        f'nota_minima:{centro.id}',
        lambda: _nota_minima_aprobacion_sql(centro),
        version=1,
        timeout=ttl(REDONDEAR_TTL),
    )


def _nota_minima_aprobacion_sql(centro):
    config = ConfiguracionCentro.objects.filter(centro=centro).first()
    if config and config.nota_minima_aprobacion is not None:
        return float(config.nota_minima_aprobacion)
    return 70.0


def _resumen_asistencia(inscripcion):
    conteo = {'presente': 0, 'tardanza': 0, 'justificado': 0, 'ausente': 0}

    for a in inscripcion.asistencias.all():
        if a.estado in conteo:
            conteo[a.estado] += 1

    total = sum(conteo.values())
    asistido = conteo['presente'] + conteo['tardanza'] + conteo['justificado']

    return {
        **conteo,
        'total': total,
        'asistido': asistido,
        'porcentaje': redondear((asistido / total) * 100) if total else None,
    }


def _asignaturas_anio(inscripcion, centro, anio, nota_minima):
    """Calcula el rendimiento por asignatura de una inscripción (reconstruido
    desde Calificacion, igual que el boletín)."""
    periodos = list(
        Periodo.objects.filter(
            estados__anio_escolar=anio,
            es_completivo=False,
        ).order_by('orden')
    )

    completivos = list(
        Periodo.objects.filter(
            estados__anio_escolar=anio,
            es_completivo=True,
        ).order_by('orden')
    )

    completivo_ids = {p.id for p in completivos}

    asignaciones = (
        DocenteMateria.objects
        .filter(
            grado=inscripcion.grado,
            seccion=inscripcion.seccion,
            anio_escolar=anio,
        )
        .select_related('asignatura', 'asignatura__area')
        .order_by('asignatura__nombre')
    )

    calificaciones = Calificacion.objects.filter(inscripcion=inscripcion)

    # notas[asignatura_id][competencia_id][periodo_id] = nota
    notas = defaultdict(lambda: defaultdict(dict))
    for c in calificaciones:
        if c.nota is not None:
            notas[c.asignatura_id][c.competencia_id][c.periodo_id] = float(c.nota)

    asignaturas = []

    for asignacion in asignaciones:
        asignatura = asignacion.asignatura
        notas_asig = notas.get(asignatura.id, {})

        notas_periodo = []
        for p in periodos:
            valores = [
                nota
                for comp in notas_asig.values()
                if (nota := comp.get(p.id)) is not None
            ]
            notas_periodo.append({
                'periodo': p.nombre,
                'promedio': (
                    redondear(sum(valores) / len(valores)) if valores else None
                ),
            })

        valores_pf = [
            v for v in (n['promedio'] for n in notas_periodo)
            if v is not None
        ]
        pf = redondear(sum(valores_pf) / len(valores_pf)) if valores_pf else None

        if pf is None:
            estado = 'sin_notas'
        elif pf >= nota_minima:
            estado = 'aprobada'
        else:
            estado = 'reprobada'

        nota_completivo = None
        aprueba_completivo = None
        if completivo_ids:
            valores = []
            for comp in notas_asig.values():
                for pid, nota in comp.items():
                    if pid in completivo_ids:
                        valores.append(nota)
            if valores:
                nota_completivo = redondear(sum(valores) / len(valores))
                aprueba_completivo = nota_completivo >= nota_minima

        asignaturas.append({
            'asignatura_id': asignatura.id,
            'asignatura': asignatura.nombre,
            'area': asignatura.area.nombre,
            'notas_periodo': notas_periodo,
            'pf': pf,
            'estado': estado,
            'nota_completivo': nota_completivo,
            'aprueba_completivo': aprueba_completivo,
        })

    return asignaturas


def _construir_anio(inscripcion, centro, anio, nota_minima):
    asignaturas = _asignaturas_anio(inscripcion, centro, anio, nota_minima)

    periodos = [
        a['periodo']
        for a in asignaturas[0]['notas_periodo']
    ] if asignaturas else [
        p.nombre for p in Periodo.objects.filter(
            estados__anio_escolar=anio,
            es_completivo=False,
        ).order_by('orden')
    ]

    tiene_completivo = Periodo.objects.filter(
        estados__anio_escolar=anio,
        es_completivo=True,
    ).exists()

    pfs = [a['pf'] for a in asignaturas if a['pf'] is not None]

    promedio_general = (
        redondear(sum(pfs) / len(pfs)) if pfs else None
    )

    observaciones = list(
        inscripcion.estudiante.observaciones.filter(
            anio_escolar=anio,
        ).order_by('-fecha')
    )

    return {
        'anio': anio,
        'inscripcion': inscripcion,
        'periodos': periodos,
        'tiene_completivo': tiene_completivo,
        'asignaturas': asignaturas,
        'promedio_general': promedio_general,
        'asistencia': _resumen_asistencia(inscripcion),
        'observaciones': observaciones,
        'estado_final': inscripcion.estado_final,
    }


def construir_kardex(estudiante, centro):
    return obtener_o_generar(
        _clave_kardex(estudiante.id, centro.id),
        lambda: _construir_kardex_sql(estudiante, centro),
        version=1,
        timeout=ttl(REDONDEAR_TTL),
    )


def _construir_kardex_sql(estudiante, centro):
    inscripciones = (
        Inscripcion.objects
        .filter(estudiante=estudiante, centro=centro)
        .select_related('grado', 'seccion', 'anio_escolar')
        .prefetch_related('asistencias')
        .order_by('anio_escolar__fecha_inicio')
    )

    nota_minima = _nota_minima_aprobacion(centro)

    anios = [
        _construir_anio(inscripcion, centro, inscripcion.anio_escolar, nota_minima)
        for inscripcion in inscripciones
    ]

    observaciones_generales = list(
        estudiante.observaciones.filter(
            anio_escolar__isnull=True,
        ).order_by('-fecha')
    )

    return {
        'estudiante': estudiante,
        'centro': centro,
        'nota_minima': nota_minima,
        'anios': anios,
        'observaciones_generales': observaciones_generales,
    }


# =========================== RECORD OFICIAL MINERD ===========================

def _primer_digito(grado):
    m = re.search(r'\d+', grado.nombre)
    return int(m.group()) if m else None


def _ciclo_nombre(nivel, grados):
    if nivel.tipo != 'secundaria':
        return f'Educación {nivel.nombre}'

    digitos = [
        d for d in (_primer_digito(g) for g in grados) if d is not None
    ]

    if digitos and all(d >= 4 for d in digitos):
        return 'Modalidad Académica (Ordenanza 22-2017)'
    if digitos and all(d <= 3 for d in digitos):
        return 'Primer Ciclo de Educación Secundaria (Ordenanzas 1-2017 y 22-2017)'
    return 'Educación Secundaria'


def _dividir_en_ciclos(grados):
    """Nivel Secundario: 1ro-3ro = Primer Ciclo, 4to-6to = Modalidad."""
    grados = sorted(grados, key=lambda g: (g.orden, g.nombre))
    if len(grados) <= 3:
        return [grados]
    return [grados[:3], grados[3:6]]


def _ultima_inscripcion_por_grado(inscripciones):
    por_grado = defaultdict(list)
    for i in inscripciones:
        por_grado[i.grado_id].append(i)
    return {
        gid: max(inscs, key=lambda i: i.anio_escolar.fecha_inicio)
        for gid, inscs in por_grado.items()
    }


def _construir_ciclo(nivel, grados, mapa_inscripciones, mapa_asignaturas):
    grados_data = []
    for grado in sorted(grados, key=lambda g: (g.orden, g.nombre)):
        insc = mapa_inscripciones[grado.id]
        asignaturas = mapa_asignaturas[insc.id]
        pfs = [a['pf'] for a in asignaturas if a['pf'] is not None]

        grados_data.append({
            'grado': grado,
            'inscripcion': insc,
            'calificacion': (
                float(insc.promedio_final)
                if insc.promedio_final is not None
                else (redondear(sum(pfs) / len(pfs)) if pfs else None)
            ),
            'fecha_aprobacion': insc.fecha_cierre,
            'asignaturas': {a['asignatura_id']: a for a in asignaturas},
        })

    # Unión de asignaturas de todos los grados del ciclo (área + nombre)
    por_id = {}
    for gd in grados_data:
        for aid, a in gd['asignaturas'].items():
            if aid not in por_id:
                por_id[aid] = a

    ids_ordenados = sorted(
        por_id,
        key=lambda aid: (por_id[aid]['area'], por_id[aid]['asignatura'])
    )

    filas = []
    for aid in ids_ordenados:
        filas.append({
            'area': por_id[aid]['area'],
            'asignatura': por_id[aid]['asignatura'],
            'celdas': [
                {
                    'calificacion': (
                        gd['asignaturas'].get(aid, {}).get('pf')
                    ),
                    'fecha': gd['inscripcion'].fecha_cierre,
                }
                for gd in grados_data
            ],
        })

    return {
        'nombre': _ciclo_nombre(nivel, grados),
        'grados': grados_data,
        'asignaturas': filas,
    }


def construir_record_notas(estudiante, centro):
    """Estructura para el RECORD DE NOTAS / ESCOLARIDAD oficial del MINERD."""
    return obtener_o_generar(
        f'record:{estudiante.id}:'
        f'{obtener_version(f"estudiante:{estudiante.id}")}:'
        f'{obtener_version(f"estructura:{centro.id}")}',
        lambda: _construir_record_sql(estudiante, centro),
        version=1,
        timeout=ttl(REDONDEAR_TTL),
    )


def _construir_record_sql(estudiante, centro):
    inscripciones = (
        Inscripcion.objects
        .filter(estudiante=estudiante, centro=centro)
        .select_related(
            'grado',
            'grado__nivel',
            'seccion',
            'anio_escolar',
        )
        .order_by('anio_escolar__fecha_inicio')
    )

    nota_minima = _nota_minima_aprobacion(centro)

    por_nivel = defaultdict(list)
    for insc in inscripciones:
        por_nivel[insc.grado.nivel_id].append(insc)

    niveles = []
    for nivel_id, inscs in por_nivel.items():
        nivel = inscs[0].grado.nivel
        grados = sorted(
            {i.grado for i in inscs},
            key=lambda g: (g.orden, g.nombre)
        )

        if nivel.tipo == 'secundaria':
            ciclos_grados = _dividir_en_ciclos(grados)
        else:
            ciclos_grados = [grados]

        mapa_inscripciones = _ultima_inscripcion_por_grado(inscs)
        mapa_asignaturas = {
            insc.id: _asignaturas_anio(
                insc, centro, insc.anio_escolar, nota_minima
            )
            for insc in inscs
        }

        ciclos = [
            _construir_ciclo(
                nivel, cg, mapa_inscripciones, mapa_asignaturas
            )
            for cg in ciclos_grados
        ]

        niveles.append({
            'nivel': nivel,
            'tipo': nivel.tipo,
            'ciclos': ciclos,
        })

    # Año en que concluyó la Educación Primaria (para el texto de certificación)
    primaria = (
        inscripciones
        .filter(grado__nivel__tipo='primaria')
        .order_by('-anio_escolar__fecha_inicio')
        .first()
    )

    return {
        'estudiante': estudiante,
        'centro': centro,
        'nota_minima': nota_minima,
        'niveles': niveles,
        'concluyo_primaria': primaria.anio_escolar.nombre if primaria else None,
        'modalidad_salida': (
            estudiante.get_modalidad_salida_display()
            if estudiante.modalidad_salida else None
        ),
    }
