"""Servicios del cierre de año escolar y promoción masiva.

Funciones puras reutilizables por vistas y comandos:
resumen de resultados, deudores al cierre, cálculo de promociones
y ejecución de la matrícula masiva del año siguiente.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count

from academico.models import Grado
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


PROMUEVE = ('aprobado',)
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

        Inscripcion.objects.create(
            estudiante=fila['estudiante'],
            centro=anio_origen.centro,
            anio_escolar=anio_destino,
            grado=fila['destino'],
            seccion_id=seccion_id,
        )
        creadas += 1

    return creadas, omitidas
