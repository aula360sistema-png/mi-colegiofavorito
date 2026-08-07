from django.db.models import Sum
from django.utils import timezone

from estudiantes.models import Estudiante, Inscripcion

from .models import AsignacionConcepto, Caja, Egreso, Pago, SesionCaja


def obtener_sesion_abierta(centro, usuario=None):
    qs = SesionCaja.objects.filter(
        centro=centro,
        estado='abierta'
    )
    if usuario:
        qs = qs.filter(usuario_apertura=usuario)
    return qs.order_by('-fecha_apertura').first()


def tiene_sesion_abierta(centro, usuario=None):
    return obtener_sesion_abierta(centro, usuario) is not None


def sesion_abierta_de_caja(caja):
    return caja.sesiones.filter(estado='abierta').first()


def cajas_disponibles(centro):
    """Cajas activas que no tienen una sesión abierta."""
    abiertas = SesionCaja.objects.filter(
        centro=centro,
        estado='abierta',
    ).values_list('caja_id', flat=True)
    return Caja.objects.filter(
        centro=centro,
        activa=True,
    ).exclude(id__in=abiertas)


def siguiente_recibo(model, centro):
    ultimo = (
        model.objects.filter(centro=centro)
        .order_by('-recibo')
        .values_list('recibo', flat=True)
        .first()
    )
    return (ultimo or 0) + 1


def pagos_de(centro, estudiante, concepto, anio):
    return (
        Pago.objects.filter(
            centro=centro,
            estudiante=estudiante,
            concepto=concepto,
            fecha__gte=anio.fecha_inicio,
            fecha__lte=anio.fecha_fin,
        )
        .aggregate(total=Sum('monto'))['total']
        or 0
    )


def periodos_recurrentes(concepto, anio):
    """Cantidad de veces que debe pagarse un concepto recurrente hasta hoy."""
    if not concepto.es_recurrente:
        return 1

    hoy = timezone.localdate()
    if hoy < anio.fecha_inicio:
        return 0
    fin = min(hoy, anio.fecha_fin)
    meses = (
        (fin.year - anio.fecha_inicio.year) * 12
        + (fin.month - anio.fecha_inicio.month)
        + 1
    )
    return max(meses, 0)


def saldo_por_concepto(centro, estudiante, concepto, anio):
    """Devuelve (esperado, pagado, saldo) para un concepto/estudiante/año.

    El saldo se calcula por montos (no por cantidad de pagos):
      - No recurrente: se cobra 1 sola vez al año (monto completo).
      - Recurrente: se cobra monto × periodos vencidos hasta hoy.
    Así, un abono (pago parcial) deja el concepto pendiente hasta que
    la suma de pagos iguale o supere el esperado.
    """
    pagado = pagos_de(centro, estudiante, concepto, anio)

    if concepto.es_recurrente:
        periodos = periodos_recurrentes(concepto, anio)
        esperado = concepto.monto * periodos
    else:
        esperado = concepto.monto

    saldo = max(esperado - pagado, 0)
    return esperado, pagado, saldo


def balance_por_concepto(centro, estudiante, anio):
    """Lista por concepto asignado: esperado, pagado, saldo."""
    asignaciones = AsignacionConcepto.objects.filter(
        centro=centro,
        estudiante=estudiante,
        anio_escolar=anio,
        activo=True,
    ).select_related('concepto')

    filas = []
    for asig in asignaciones:
        esperado, pagado, saldo = saldo_por_concepto(
            centro,
            estudiante,
            asig.concepto,
            anio,
        )
        filas.append({
            'concepto': asig.concepto,
            'esperado': esperado,
            'pagado': pagado,
            'saldo': saldo,
        })
    return filas


def balance_estudiante(centro, estudiante, anio):
    """Devuelve (esperado, pagado, saldo) del estudiante en el año dado."""
    esperado = 0
    pagado = 0

    for f in balance_por_concepto(centro, estudiante, anio):
        esperado += f['esperado']
        pagado += f['pagado']

    saldo = max(esperado - pagado, 0)

    return {
        'esperado': esperado,
        'pagado': pagado,
        'saldo': saldo,
    }


def calcular_cuentas_por_cobrar(centro, anio):
    """Lista de estudiantes con saldo pendiente, ordenada por deuda desc."""
    asignaciones = (
        AsignacionConcepto.objects
        .filter(centro=centro, anio_escolar=anio, activo=True)
        .select_related('estudiante', 'concepto')
    )

    estudiantes = set()
    for asig in asignaciones:
        estudiantes.add(asig.estudiante_id)

    filas = []
    for estudiante in Estudiante.objects.filter(
        id__in=estudiantes,
        centro=centro,
    ).order_by('primer_apellido', 'primer_nombre'):
        datos = balance_estudiante(centro, estudiante, anio)
        if datos['saldo'] > 0:
            filas.append({
                'estudiante': estudiante,
                'esperado': datos['esperado'],
                'pagado': datos['pagado'],
                'saldo': datos['saldo'],
            })

    filas.sort(key=lambda f: f['saldo'], reverse=True)
    return filas


def calcular_cuentas_por_cobrar_detalle(centro, anio):
    """Lista por (estudiante, concepto) con saldo pendiente > 0.

    Cada fila lleva el concepto pendiente para poder cobrar exactamente
    ese concepto desde la tabla de cuentas por cobrar.
    """
    asignaciones = (
        AsignacionConcepto.objects
        .filter(centro=centro, anio_escolar=anio, activo=True)
        .select_related('estudiante', 'concepto')
        .order_by(
            'estudiante__primer_apellido',
            'estudiante__primer_nombre',
            'concepto__nombre',
        )
    )

    filas = []
    vistos = set()

    inscritos = set(
        Inscripcion.objects.filter(
            centro=centro,
            anio_escolar=anio,
        ).values_list('estudiante_id', flat=True)
    )

    for asig in asignaciones:
        if asig.estudiante_id not in inscritos:
            continue

        clave = (asig.estudiante_id, asig.concepto_id)
        if clave in vistos:
            continue
        vistos.add(clave)

        esperado, pagado, saldo = saldo_por_concepto(
            centro,
            asig.estudiante,
            asig.concepto,
            anio,
        )
        if saldo > 0:
            filas.append({
                'estudiante': asig.estudiante,
                'concepto': asig.concepto,
                'esperado': esperado,
                'pagado': pagado,
                'saldo': saldo,
            })

    filas.sort(key=lambda f: f['saldo'], reverse=True)
    return filas
