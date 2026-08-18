from django.db.models import Sum
from django.utils import timezone

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from estudiantes.models import Estudiante, Inscripcion

from .models import AsignacionConcepto, Caja, Egreso, Pago, SesionCaja

TTL_CAJA = 'CACHE_TTL_MEDIO'


def invalidar_pagos_centro(centro_id):
    """Invalida balances, cuentas por cobrar y listas de pagos/egresos
    de un centro cuando cambia su movimiento de caja."""
    invalidar_dominio(f'pagos:{centro_id}')


def _version_pagos(centro_id):
    return obtener_version(f'pagos:{centro_id}')


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


def pagos_del_centro(centro):
    """Todos los pagos del centro (datos base para listas y reportes).

    Se cachea con el dominio `pagos:{centro}`. La vista filtra en memoria
    para no re-consultar la BD en cada combinación de filtros.
    """
    clave = f'pagos_lista:{centro.id}:{_version_pagos(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(
            Pago.objects.filter(centro=centro).select_related(
                'estudiante', 'concepto', 'sesion'
            ).order_by('-fecha', '-id')
        ),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def egresos_del_centro(centro):
    """Todos los egresos del centro (datos base para listas y reportes)."""
    clave = f'egresos_lista:{centro.id}:{_version_pagos(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(
            Egreso.objects.filter(centro=centro).select_related(
                'sesion'
            ).order_by('-fecha', '-id')
        ),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def metricas_dia(centro, fecha):
    """Resumen de caja de un día (inicio de caja) cacheado por dominio."""
    clave = (
        f'caja_inicio:{centro.id}:{fecha.isoformat()}:'
        f'{_version_pagos(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _metricas_dia_sql(centro, fecha),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def _metricas_dia_sql(centro, fecha):
    pagos = Pago.objects.filter(centro=centro, fecha=fecha)
    egresos = Egreso.objects.filter(centro=centro, fecha=fecha)
    return {
        'entradas_hoy': pagos.aggregate(t=Sum('monto'))['t'] or 0,
        'salidas_hoy': egresos.aggregate(t=Sum('monto'))['t'] or 0,
        'pagos_hoy': list(
            pagos.select_related('estudiante', 'concepto').order_by('-id')[:6]
        ),
        'egresos_hoy': list(egresos.order_by('-id')[:6]),
        'total_entradas': (
            Pago.objects.filter(centro=centro)
            .aggregate(t=Sum('monto'))['t'] or 0
        ),
        'total_salidas': (
            Egreso.objects.filter(centro=centro)
            .aggregate(t=Sum('monto'))['t'] or 0
        ),
    }


def metricas_reporte_diario(centro, fecha, caja_id=None):
    """Agregados del reporte diario cacheados por (centro, fecha, caja)."""
    clave = (
        f'reporte_diario:{centro.id}:{fecha.isoformat()}:'
        f'{caja_id or 0}:{_version_pagos(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _metricas_reporte_diario_sql(centro, fecha, caja_id),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def _metricas_reporte_diario_sql(centro, fecha, caja_id=None):
    from django.db.models import Count

    pagos = Pago.objects.filter(centro=centro, fecha=fecha)
    egresos = Egreso.objects.filter(centro=centro, fecha=fecha)

    if caja_id:
        pagos = pagos.filter(sesion__caja_id=caja_id)
        egresos = egresos.filter(sesion__caja_id=caja_id)

    METODO_LABELS = dict(Pago.METODO_PAGO_CHOICES)

    def _con_metodo(qs):
        return [
            {
                'metodo': m['metodo_pago'],
                'label': METODO_LABELS.get(m['metodo_pago'], m['metodo_pago']),
                'total': m['total'],
                'cantidad': m['cantidad'],
            }
            for m in qs
        ]

    entradas = pagos.aggregate(t=Sum('monto'))['t'] or 0
    salidas = egresos.aggregate(t=Sum('monto'))['t'] or 0

    return {
        'entradas': entradas,
        'salidas': salidas,
        'neto': entradas - salidas,
        'cantidad_pagos': pagos.count(),
        'cantidad_egresos': egresos.count(),
        'por_concepto': list(
            pagos.values('concepto__nombre')
            .annotate(total=Sum('monto'), cantidad=Count('id'))
        ),
        'por_metodo_pago': _con_metodo(
            pagos.values('metodo_pago')
            .annotate(total=Sum('monto'), cantidad=Count('id'))
        ),
        'por_metodo_egreso': _con_metodo(
            egresos.values('metodo_pago')
            .annotate(total=Sum('monto'), cantidad=Count('id'))
        ),
    }


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
    """Lista por concepto asignado: esperado, pagado, saldo.

    Cacheada por (centro, estudiante, año). Se invalida con el dominio
    `pagos:{centro}` (cambio en pagos, egresos o asignaciones).
    """
    clave = (
        f'balance:{centro.id}:{estudiante.id}:{anio.id}:'
        f'{_version_pagos(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _balance_por_concepto_sql(centro, estudiante, anio),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def _balance_por_concepto_sql(centro, estudiante, anio):
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


def deuda_detalle_estudiante(centro, estudiante, anio=None):
    """Desglose de deuda pendiente de un estudiante en el año dado.

    Separa la deuda en:
      - ``vencida``: cuotas de meses anteriores al actual (y el actual si
        ya pasó) que no han sido pagadas.
      - ``proxima``: cuota del mes en curso que aún no vence.

    Reutiliza los balances cacheados por (centro, estudiante, año).
    """
    import calendar

    from core.models import AnioEscolar

    if anio is None:
        anio = (
            AnioEscolar.objects
            .filter(centro=centro, activo=True)
            .first()
        )

    vacia = {
        'saldo_total': 0,
        'vencida': 0,
        'proxima': 0,
        'vencidas': [],
        'proximas': [],
        'tiene_deuda': False,
    }

    if anio is None:
        return vacia

    hoy = timezone.localdate()
    hoy_fin_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    mes_actual_vencido = hoy.day >= hoy_fin_mes

    vencidas = []
    proximas = []
    total_saldo = 0
    total_vencida = 0
    total_proxima = 0

    for f in balance_por_concepto(centro, estudiante, anio):
        saldo = f['saldo']
        if saldo <= 0:
            continue

        concepto = f['concepto']
        monto = float(concepto.monto) or 0
        total_saldo += saldo

        if not concepto.es_recurrente or monto <= 0:
            # No recurrente o sin monto definido: toda la deuda está vencida.
            vencidas.append({
                'concepto': concepto,
                'cantidad': 1,
                'monto': saldo,
            })
            total_vencida += saldo
            continue

        periodos = periodos_recurrentes(concepto, anio)
        cuotas_pagadas = int(float(f['pagado']) / monto)
        cuotas_impagas = max(periodos - cuotas_pagadas, 1)

        # Índice (0-based) de la cuota del mes en curso dentro del año.
        indice_actual = (
            (hoy.year - anio.fecha_inicio.year) * 12
            + (hoy.month - anio.fecha_inicio.month)
        )
        if mes_actual_vencido:
            indice_actual += 1

        # Los pagos cubren primero las cuotas más antiguas (FIFO): las
        # vencidas son las cuotas vencidas por calendario aún sin pagar.
        vencidas_calendario = min(indice_actual, periodos)
        cantidad_vencida = max(vencidas_calendario - cuotas_pagadas, 0)
        cantidad_vencida = min(cantidad_vencida, cuotas_impagas)
        cantidad_proxima = cuotas_impagas - cantidad_vencida

        if cantidad_vencida:
            vencidas.append({
                'concepto': concepto,
                'cantidad': cantidad_vencida,
                'monto': cantidad_vencida * monto,
            })
            total_vencida += cantidad_vencida * monto

        if cantidad_proxima:
            proximas.append({
                'concepto': concepto,
                'cantidad': cantidad_proxima,
                'monto': cantidad_proxima * monto,
            })
            total_proxima += cantidad_proxima * monto

    return {
        'saldo_total': total_saldo,
        'vencida': total_vencida,
        'proxima': total_proxima,
        'vencidas': vencidas,
        'proximas': proximas,
        'tiene_deuda': total_saldo > 0,
    }


def tiene_deuda_pendiente(centro, estudiante, anio=None):
    """True si el estudiante tiene cualquier saldo pendiente en el año."""
    return deuda_detalle_estudiante(centro, estudiante, anio)['tiene_deuda']


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
    if anio is None:
        return []

    clave = (
        f'cxc:{centro.id}:{anio.id}:'
        f'{_version_pagos(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _calcular_cuentas_por_cobrar_sql(centro, anio),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def _calcular_cuentas_por_cobrar_sql(centro, anio):
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

    Es la consulta más pesada del módulo de caja (patrón N+1), por eso
    se cachea con el dominio `pagos:{centro}`.
    """
    if anio is None:
        return []

    clave = (
        f'cxc_detalle:{centro.id}:{anio.id}:'
        f'{_version_pagos(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _calcular_cuentas_por_cobrar_detalle_sql(centro, anio),
        version=1,
        timeout=ttl(TTL_CAJA),
    )


def _calcular_cuentas_por_cobrar_detalle_sql(centro, anio):
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
