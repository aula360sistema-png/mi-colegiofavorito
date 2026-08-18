from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)

from .models import Factura, FacturaItem, SecuenciaNCF, TASA_ITBIS, TipoComprobante

TTL_FACTURAS = 'CACHE_TTL_MEDIO'


def invalidar_facturas_centro(centro_id):
    """Invalida listas y métricas de facturación de un centro."""
    invalidar_dominio(f'facturas:{centro_id}')


def _version_facturas(centro_id):
    return obtener_version(f'facturas:{centro_id}')


def _redondear(valor):
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def tipo_comprobante_predeterminado(centro):
    """Tipo por defecto del centro: 32 Consumo Electrónica si existe, si no el primer activo."""
    tipo = TipoComprobante.objects.filter(codigo='32', activo=True).first()
    if tipo:
        return tipo
    return TipoComprobante.objects.filter(activo=True).first()


def siguiente_ncf(centro, tipo):
    """Genera el siguiente e-NCF para un centro y tipo de comprobante.

    Formato DGII (13 caracteres): serie E + tipo (2 dígitos) + correlativo
    de 10 dígitos (ej: E320000000001).
    El incremento es atómico (select_for_update) para evitar duplicados.
    """
    with transaction.atomic():
        secuencia, _ = SecuenciaNCF.objects.select_for_update().get_or_create(
            centro=centro,
            tipo=tipo,
            defaults={'ultimo_numero': 0, 'activo': True},
        )
        secuencia.ultimo_numero += 1
        secuencia.save(update_fields=['ultimo_numero'])
        return f"{tipo.letra}{tipo.codigo}{secuencia.ultimo_numero:010d}"


def emitir_factura(pago, aplicar_itbis=False, usuario=None):
    """Crea la factura del pago con su línea de detalle y su NCF.

    Un pago solo puede tener una factura; si ya existe, devuelve la actual.
    """
    existente = getattr(pago, 'factura', None)
    if existente:
        return existente

    tipo = tipo_comprobante_predeterminado(pago.centro)
    subtotal = pago.monto
    itbis = _redondear(subtotal * TASA_ITBIS) if aplicar_itbis else Decimal('0.00')
    total = _redondear(subtotal + itbis)

    with transaction.atomic():
        factura = Factura.objects.create(
            centro=pago.centro,
            ncf=siguiente_ncf(pago.centro, tipo) if tipo else '',
            tipo=tipo,
            pago=pago,
            estudiante=pago.estudiante,
            subtotal=subtotal,
            itbis=itbis,
            total=total,
            aplica_itbis=aplicar_itbis,
            fecha=pago.fecha,
            creado_por=usuario,
        )
        FacturaItem.objects.create(
            factura=factura,
            concepto=pago.concepto,
            descripcion=pago.concepto.nombre,
            cantidad=1,
            precio=pago.monto,
            subtotal=pago.monto,
        )

    return factura


def facturas_del_centro(centro):
    """Todas las facturas del centro (datos base para listas y métricas).

    Se cachea con el dominio `facturas:{centro}`. La vista filtra en memoria.
    """
    clave = f'facturas_lista:{centro.id}:{_version_facturas(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(
            Factura.objects.filter(centro=centro).select_related(
                'estudiante', 'tipo', 'pago'
            ).order_by('-fecha', '-id')
        ),
        version=1,
        timeout=ttl(TTL_FACTURAS),
    )


def metricas_facturas(centro, anio):
    """KPIs de facturación del año (inicio) cacheados por dominio."""
    clave = (
        f'facturas_inicio:{centro.id}:'
        f'{anio.id if anio else 0}:{_version_facturas(centro.id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _metricas_facturas_sql(centro, anio),
        version=1,
        timeout=ttl(TTL_FACTURAS),
    )


def _metricas_facturas_sql(centro, anio):
    from django.utils import timezone

    facturas = Factura.objects.filter(centro=centro)

    qs_anio = (
        facturas.filter(
            fecha__gte=anio.fecha_inicio,
            fecha__lte=anio.fecha_fin,
        )
        if anio
        else facturas.none()
    )

    hoy = timezone.localdate()
    return {
        'total_facturado': qs_anio.aggregate(t=Sum('total'))['t'] or 0,
        'total_itbis': qs_anio.aggregate(t=Sum('itbis'))['t'] or 0,
        'cantidad_facturas': qs_anio.count(),
        'facturas_hoy': list(
            facturas.filter(fecha=hoy)
            .select_related('estudiante', 'tipo', 'pago')
            .order_by('-id')[:6]
        ),
        'facturas_recientes': list(
            qs_anio.select_related('estudiante', 'tipo', 'pago')
            .order_by('-fecha', '-id')[:8]
        ),
    }
