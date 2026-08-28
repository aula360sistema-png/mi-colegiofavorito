"""Servicios del cierre de año escolar y promoción masiva.

Funciones puras reutilizables por vistas y comandos:
resumen de resultados, deudores al cierre, cálculo de promociones,
ejecución de la matrícula masiva del año siguiente y validación de
notas pendientes antes de cerrar períodos.
"""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Count

from academico.models import (
    Calificacion,
    Competencia,
    DocenteMateria,
    Grado,
    Seccion,
)
from caja.services import deuda_detalle_estudiante
from estudiantes.models import HistorialAcademico, Inscripcion


def resumen_cierre(anio):
    """Totales de inscripciones del año agrupados por estado final."""
    totales = {'inscritos': 0}
    for valor, _nombre in Inscripcion.ESTADO_FINALES:
        totales[valor] = 0

    filas = (
        Inscripcion.objects
        .filter(anio_escolar=anio)
        .values('estado_final')
        .annotate(total=Count('id'))
    )
    for fila in filas:
        totales[fila['estado_final']] = fila['total']
        totales['inscritos'] += fila['total']
    return totales


def deudores_del_anio(centro, anio):
    """Estudiantes del año con saldo pendiente en caja.

    Devuelve (lista, total). Sin módulo de caja la lista es vacía
    (modo neutral, igual que el resto de los flujos financieros).
    """
    from core.services import modulo_activo
    if not modulo_activo(centro.id, 'caja'):
        return [], Decimal('0.00')

    deudores = []
    total = Decimal('0.00')

    inscripciones = (
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio)
        .select_related('estudiante', 'grado')
    )

    for inscripcion in inscripciones:
        detalle = deuda_detalle_estudiante(
            centro,
            inscripcion.estudiante,
            anio,
        )
        saldo = detalle.get('saldo_total') or Decimal('0')
        if saldo > 0:
            deudores.append({
                'matricula': inscripcion.estudiante.matricula,
                'nombre': inscripcion.estudiante.nombre_completo(),
                'grado': str(inscripcion.grado),
                'saldo': str(saldo),
            })
            total += Decimal(str(saldo))

    return deudores, total


def grado_siguiente(grado):
    """Grado consecutivo dentro del mismo nivel (None si es el último)."""
    return (
        Grado.objects
        .filter(nivel=grado.nivel, orden__gt=grado.orden)
        .order_by('orden', 'nombre')
        .first()
    )


PROMUEVE = ('aprobado', 'promocion_condicional')
REPITE = ('reprobado', 'recuperacion', 'sin_calificacion')


def calcular_promociones(anio_origen):
    """Plan de promoción masiva a partir de un año cerrado.

    Devuelve lista de dicts:
      estudiante, grado_actual, estado, destino (Grado|None), accion
    donde accion ∈ {promover, repetir, egresado, omitir}.
    """
    plan = []

    inscripciones = (
        Inscripcion.objects
        .filter(anio_escolar=anio_origen)
        .select_related('estudiante', 'grado', 'seccion')
        .order_by(
            'grado__orden',
            'seccion__nombre',
            'estudiante__primer_apellido',
            'estudiante__primer_nombre',
        )
    )

    for inscripcion in inscripciones:
        estado = inscripcion.estado_final

        if estado == 'retirado':
            accion, destino = 'omitir', None
        elif estado in PROMUEVE:
            destino = grado_siguiente(inscripcion.grado)
            accion = 'promover' if destino else 'egresado'
        elif estado in REPITE:
            destino, accion = inscripcion.grado, 'repetir'
        else:
            accion, destino = 'omitir', None

        plan.append({
            'estudiante': inscripcion.estudiante,
            'grado_actual': inscripcion.grado,
            'estado': estado,
            'destino': destino,
            'accion': accion,
        })

    return plan


@transaction.atomic
def ejecutar_promocion(anio_origen, anio_destino, usuario,
                       secciones_por_grado, solo_estudiantes=None):
    """Inscribe en ``anio_destino`` según el plan calculado.

    ``secciones_por_grado``: {grado_id: seccion_id} elegido por el
    director en la previsualización. ``solo_estudiantes`` limita la
    ejecución a esos ids (casilla por estudiante).

    Devuelve (creadas, omitidas).
    """
    creadas = omitidas = 0
    # Contador en memoria de asignaciones por sección para respetar el
    # cupo durante la promoción masiva (sin reconsultar DB por fila).
    from .cupo import cantidad_ocupada, hay_cupo_disponible

    secciones_validas = {}
    for grado_id, sec_id in secciones_por_grado.items():
        seccion = Seccion.objects.filter(
            centro=anio_origen.centro, pk=sec_id
        ).first()
        if seccion:
            secciones_validas[int(grado_id)] = (
                seccion,
                cantidad_ocupada(seccion, Grado.objects.filter(pk=grado_id).first(), anio_destino),
            )

    existentes = set(
        Inscripcion.objects.filter(
            anio_escolar=anio_destino,
            centro=anio_origen.centro,
        ).values_list('estudiante_id', flat=True)
    )

    for fila in calcular_promociones(anio_origen):
        if fila['accion'] not in ('promover', 'repetir'):
            omitidas += 1
            continue

        if (solo_estudiantes is not None
                and fila['estudiante'].id not in solo_estudiantes):
            omitidas += 1
            continue

        if fila['estudiante'].id in existentes:
            omitidas += 1
            continue

        seccion_id = secciones_por_grado.get(str(fila['destino'].id))
        if not seccion_id:
            omitidas += 1
            continue

        # Valida cupo de la sección destino (si tiene límite).
        info_seccion = secciones_validas.get(fila['destino'].id)
        if info_seccion:
            seccion_destino, ocupados = info_seccion
            if seccion_destino.capacidad_max is not None \
                    and ocupados >= seccion_destino.capacidad_max:
                omitidas += 1
                continue

        Inscripcion.objects.create(
            estudiante=fila['estudiante'],
            centro=anio_origen.centro,
            anio_escolar=anio_destino,
            grado=fila['destino'],
            seccion_id=seccion_id,
        )
        creadas += 1
        if info_seccion:
            secciones_validas[fila['destino'].id] = (
                info_seccion[0], info_seccion[1] + 1,
            )

    return creadas, omitidas


# =====================================================
# VALIDACIÓN DE NOTAS PENDIENTES AL CERRAR PERÍODOS
# =====================================================

def _matriz_faltantes(anio, periodo):
    """Matriz de calificaciones faltantes de un período.

    Devuelve (faltantes, nombres, por_asignacion) donde:
      faltantes:      {(inscripcion_id, asignatura_id): {competencia_id..}}
      nombres:        {inscripcion_id: nombre_completo}
      por_asignacion: {docentemateria_id: [inscripcion_id..]} con los
                      estudiantes con notas incompletas de esa asignación

    Reglas de expectativa:
      - Se excluyen los estudiantes retirados.
      - En períodos de completivo solo se exige nota a quienes quedaron
        en 'recuperacion' (los únicos que lo cursan).
      - Si un nivel no tiene competencias activas no hay nada exigible.
    """
    asignaciones = list(
        DocenteMateria.objects.filter(anio_escolar=anio)
        .select_related('asignatura', 'grado', 'grado__nivel')
    )
    if not asignaciones:
        return {}, {}, {}

    inscripciones = list(
        Inscripcion.objects
        .filter(anio_escolar=anio)
        .exclude(estado_final='retirado')
        .values_list('id', 'estado_final', 'grado_id', 'seccion_id',
                     'estudiante__primer_nombre',
                     'estudiante__segundo_nombre',
                     'estudiante__primer_apellido',
                     'estudiante__segundo_apellido')
    )
    if not inscripciones:
        return {}, {}, {}

    if periodo.es_completivo:
        esperados = [
            i for i in inscripciones if i[1] == 'recuperacion'
        ]
    else:
        esperados = list(inscripciones)

    def _nombre(fila):
        partes = fila[4:8]
        return ' '.join(p for p in partes if p).strip()

    nombres = {fila[0]: _nombre(fila) for fila in esperados}
    ids_esperados = set(nombres)
    ubicacion = {
        fila[0]: (fila[2], fila[3]) for fila in esperados
    }

    competencias_por_nivel = defaultdict(set)
    for nivel_id, comp_id in (
        Competencia.objects
        .filter(activo=True, nivel__centro=anio.centro)
        .values_list('nivel_id', 'id')
    ):
        competencias_por_nivel[nivel_id].add(comp_id)

    registradas = defaultdict(set)
    filas = (
        Calificacion.objects
        .filter(periodo=periodo, inscripcion__in=ids_esperados)
        .values_list('inscripcion_id', 'asignatura_id', 'competencia_id')
    )
    for ins_id, asig_id, comp_id in filas:
        registradas[(ins_id, asig_id)].add(comp_id)

    faltantes = {}
    por_asignacion = {}
    for asig in asignaciones:
        requeridas = competencias_por_nivel.get(asig.grado.nivel_id)
        if not requeridas:
            continue
        pendientes_asig = []
        for ins_id in ids_esperados:
            if ubicacion[ins_id] != (asig.grado_id, asig.seccion_id):
                continue
            tiene = registradas.get((ins_id, asig.asignatura_id), set())
            debe = requeridas - tiene
            if debe:
                faltantes[(ins_id, asig.asignatura_id)] = debe
                pendientes_asig.append(ins_id)
        if pendientes_asig:
            por_asignacion[asig.id] = sorted(pendientes_asig)

    return faltantes, nombres, por_asignacion


def pendientes_por_docente(anio, periodo):
    """Reporte de notas pendientes por docente/asignatura/sección.

    Para cada DocenteMateria del año verifica que cada estudiante
    matriculado tenga Calificacion para todas las competencias activas
    del nivel en ese período. Devuelve lista de dicts ordenada:
      {docente, asignatura, grado, seccion, faltantes, inscripciones}
    """
    _faltantes, nombres, por_asignacion = _matriz_faltantes(anio, periodo)
    if not por_asignacion:
        return []

    reporte = []
    for asig in DocenteMateria.objects.filter(
        id__in=por_asignacion,
    ).select_related('docente', 'asignatura', 'grado', 'seccion'):
        ids = por_asignacion.get(asig.id) or []
        reporte.append({
            'docente': str(asig.docente),
            'asignatura': asig.asignatura.nombre,
            'grado': str(asig.grado),
            'seccion': str(asig.seccion),
            'faltantes': len(ids),
            'nombres': [nombres.get(i, '?') for i in ids],
            'inscripciones': list(ids),
        })

    reporte.sort(key=lambda r: (r['grado'], r['seccion'], r['asignatura']))
    return reporte


@transaction.atomic
def rellenar_ceros_periodo(anio, periodo):
    """Completa con nota 0 (origen='sistema') lo pendiente del período.

    Solo debe invocarse desde el flujo de cierre FORZADO autorizado por
    Dirección: deja trazabilidad en Calificacion.origen y devuelve la
    cantidad de notas creadas.
    """
    faltantes, _nombres, _por_asignacion = _matriz_faltantes(anio, periodo)
    if not faltantes:
        return 0

    objetos = [
        Calificacion(
            inscripcion_id=ins_id,
            asignatura_id=asig_id,
            competencia_id=comp_id,
            periodo=periodo,
            nota=Decimal('0'),
            origen='sistema',
        )
        for (ins_id, asig_id), comps in faltantes.items()
        for comp_id in comps
    ]

    Calificacion.objects.bulk_create(objetos, batch_size=500)
    return len(objetos)
