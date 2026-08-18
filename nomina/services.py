from datetime import date, timedelta

import logging

from dateutil.relativedelta import relativedelta

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ValidationError

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from core.models import ConfiguracionCentro

from comunicaciones.services.email import enviar_email_con_pdf

from .pdf import generar_pdf_boleta

from .models import (
    ConfiguracionNomina,
    IngresoEmpleado,
    DescuentoEmpleado,
    Nomina,
    IngresoNomina,
    DescuentoNomina,
    PeriodoNomina,
    TipoDescuento,
    TipoIngreso
)

logger = logging.getLogger(__name__)

CENTAVOS = Decimal('0.01')

MESES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

ESTADOS_ACTIVOS = ['GENERADA', 'REVISADA', 'APROBADA', 'PAGADA']


# =========================================================
# FACTORES DE PRORRATEO POR TIPO DE PAGO
# =========================================================
#
# El salario_base y los montos fijos (ingresos/descuentos del
# empleado) se registran SIEMPRE como montos mensuales. Según el
# tipo de pago del centro, cada período paga una fracción:
#   - Mensual    → 1      (12 períodos por año)
#   - Quincenal  → 1/2    (24 períodos por año)
#   - Semanal    → 12/52  (52 períodos por año)
# =========================================================


def factor_periodo(tipo_pago):
    """Fracción del monto mensual que corresponde a cada período."""
    tipo = (tipo_pago or 'mensual').lower()

    if tipo == 'quincenal':
        return Decimal('0.50')

    if tipo == 'semanal':
        return Decimal('12') / Decimal('52')

    return Decimal('1.00')


def periodos_por_anio(tipo_pago):
    """Cantidad de períodos de pago por año (para anualizar el ISR)."""
    tipo = (tipo_pago or 'mensual').lower()

    if tipo == 'quincenal':
        return 24

    if tipo == 'semanal':
        return 52

    return 12


def tipo_pago_del_centro(centro_id):
    config = ConfiguracionCentro.objects.filter(
        centro_id=centro_id
    ).first()
    return config.tipo_pago_nomina if config else 'mensual'


def redondear(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


# =========================================================
# IMPUESTO SOBRE LA RENTA (ISR) — ESCALA DGII
# =========================================================
#
# Escala anual vigente en República Dominicana (DGII):
#   - Hasta RD$ 416,220.00            → Exento
#   - 416,220.01 a 624,329.00         → 15% del excedente sobre 416,220
#   - 624,329.01 a 867,123.00         → 31,216.35 + 20% excedente
#   - 867,123.01 en adelante          → 79,776.15 + 25% excedente
#
# El ISR se calcula sobre el salario gravable (ingresos del período
# menos aportes TSS del empleado: AFP + ARS), se anualiza y luego se
# divide entre la cantidad de períodos del año.
# =========================================================

LIMITE_EXENTO = Decimal('416220.00')
LIMITE_15 = Decimal('624329.00')
LIMITE_20 = Decimal('867123.00')

TASA_15 = Decimal('0.15')
TASA_20 = Decimal('0.20')
TASA_25 = Decimal('0.25')

BASE_20 = Decimal('31216.35')
BASE_25 = Decimal('79776.15')


def calcular_isr(salario_gravable, periodos_por_anio_val):
    """Calcula el ISR del período a partir del salario gravable del período."""
    if salario_gravable <= 0 or not periodos_por_anio_val:
        return Decimal('0.00')

    anual = salario_gravable * Decimal(periodos_por_anio_val)

    if anual <= LIMITE_EXENTO:
        isr_anual = Decimal('0.00')

    elif anual <= LIMITE_15:
        isr_anual = (anual - LIMITE_EXENTO) * TASA_15

    elif anual <= LIMITE_20:
        isr_anual = BASE_20 + (anual - LIMITE_15) * TASA_20

    else:
        isr_anual = BASE_25 + (anual - LIMITE_20) * TASA_25

    isr_periodo = isr_anual / Decimal(periodos_por_anio_val)

    return max(redondear(isr_periodo), Decimal('0.00'))


# =========================================================
# TIPOS OBLIGATORIOS (Salario Base / ISR)
# =========================================================

def tipo_ingreso_salario_base():
    """Devuelve (creándolo si falta) el TipoIngreso 'Salario Base'."""
    tipo, _ = TipoIngreso.objects.get_or_create(
        nombre__iexact='Salario Base',
        defaults={
            'nombre': 'Salario Base',
            'obligatorio': True,
            'activo': True,
        }
    )
    return tipo


def tipo_descuento_isr():
    """Devuelve (creándolo si falta) el TipoDescuento 'ISR'.

    El ISR se puede desactivar poniendo `activo=False`; en ese caso
    la nómina deja de calcularlo.
    """
    tipo, _ = TipoDescuento.objects.get_or_create(
        nombre__iexact='ISR',
        defaults={
            'nombre': 'ISR',
            'porcentaje': 0,
            'es_porcentaje': False,
            'obligatorio': True,
            'activo': True,
        }
    )
    return tipo


# =========================================================
# GENERAR NOMINA
# =========================================================

@transaction.atomic
def generar_nomina(periodo, centro_id, generado_por=None):

    """Motor de nómina: prorratea salarios, aplica TSS e ISR
    y registra el detalle de ingresos y descuentos por empleado."""

    if periodo.nomina_generada:
        raise ValidationError(
            "La nómina de este período ya fue generada."
        )

    # Limpieza defensiva: si el período tiene nóminas previas pero el flag
    # no quedó marcado (estado inconsistente), se eliminan para poder
    # regenerar sin chocar con la unicidad (periodo, usuario).
    if periodo.nominas.exists():
        periodo.nominas.all().delete()

    tipo_pago = tipo_pago_del_centro(centro_id)
    factor = factor_periodo(tipo_pago)
    ppa = periodos_por_anio(tipo_pago)

    # =====================================================
    # CONFIGURACIONES ACTIVAS
    # =====================================================

    empleados = ConfiguracionNomina.objects.filter(
        centro_id=centro_id,
        activo_nomina=True,
        usuario__is_active=True
    ).select_related(
        'usuario',
        'cargo',
        'afp',
        'ars'
    )

    if not empleados.exists():
        raise ValidationError(
            "No existen empleados activos para nómina."
        )

    tipo_salario = tipo_ingreso_salario_base()

    tipo_afp = TipoDescuento.objects.filter(
        nombre__iexact='AFP'
    ).first()

    tipo_ars = TipoDescuento.objects.filter(
        nombre__iexact='ARS'
    ).first()

    tipo_isr = tipo_descuento_isr()
    usar_isr = tipo_isr.activo

    descuentos_globales = (
        TipoDescuento.objects
        .filter(activo=True, obligatorio=True)
        .exclude(nombre__in=['AFP', 'ARS', 'ISR'])
    )

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================

    for emp in empleados:

        salario_base_mensual = emp.salario_base or Decimal('0.00')
        salario_base_periodo = redondear(salario_base_mensual * factor)

        total_ingresos = Decimal('0.00')
        total_descuentos = Decimal('0.00')

        nomina = Nomina.objects.create(
            periodo=periodo,
            usuario=emp.usuario,
            configuracion=emp,
            salario_base=salario_base_periodo,
            total_ingresos=0,
            total_descuentos=0,
            neto_pagar=0,
            pagado=False,
            generado_por=generado_por,
        )

        # =================================================
        # 1. SALARIO BASE (prorrateado)
        # =================================================

        IngresoNomina.objects.create(
            nomina=nomina,
            tipo=tipo_salario,
            descripcion=f"Salario Base ({tipo_pago})",
            monto=salario_base_periodo
        )

        total_ingresos += salario_base_periodo

        # =================================================
        # 2. INGRESOS EXTRA (prorrateados)
        # =================================================

        ingresos = IngresoEmpleado.objects.filter(
            configuracion=emp,
            activo=True
        ).select_related('tipo')

        for ingreso in ingresos:
            monto = redondear(ingreso.monto * factor)
            IngresoNomina.objects.create(
                nomina=nomina,
                tipo=ingreso.tipo,
                descripcion=ingreso.tipo.nombre,
                monto=monto
            )
            total_ingresos += monto

        # =================================================
        # 3. AFP
        # =================================================

        monto_afp = Decimal('0.00')

        if emp.afp:
            monto_afp = redondear(
                salario_base_periodo * emp.afp.porcentaje_empleado / 100
            )
            if tipo_afp:
                DescuentoNomina.objects.create(
                    nomina=nomina,
                    tipo=tipo_afp,
                    descripcion=f'AFP {emp.afp.nombre}',
                    monto=monto_afp
                )
                total_descuentos += monto_afp

        # =================================================
        # 4. ARS
        # =================================================

        monto_ars = Decimal('0.00')

        if emp.ars:
            monto_ars = redondear(
                salario_base_periodo * emp.ars.porcentaje_empleado / 100
            )
            if tipo_ars:
                DescuentoNomina.objects.create(
                    nomina=nomina,
                    tipo=tipo_ars,
                    descripcion=f'ARS {emp.ars.nombre}',
                    monto=monto_ars
                )
                total_descuentos += monto_ars

        # =================================================
        # 5. DESCUENTOS GLOBALES OBLIGATORIOS
        # =================================================

        for descuento in descuentos_globales:
            if descuento.es_porcentaje:
                monto = redondear(
                    salario_base_periodo * descuento.porcentaje / 100
                )
            else:
                monto = redondear(descuento.porcentaje * factor)

            if monto <= 0:
                continue

            DescuentoNomina.objects.create(
                nomina=nomina,
                tipo=descuento,
                descripcion=descuento.nombre,
                monto=monto
            )
            total_descuentos += monto

        # =================================================
        # 6. DESCUENTOS PERSONALIZADOS (prorrateados)
        # =================================================

        descuentos_personales = DescuentoEmpleado.objects.filter(
            configuracion=emp,
            activo=True
        ).select_related('tipo')

        for descuento in descuentos_personales:
            monto = redondear(descuento.monto * factor)
            DescuentoNomina.objects.create(
                nomina=nomina,
                tipo=descuento.tipo,
                descripcion=descuento.tipo.nombre,
                monto=monto
            )
            total_descuentos += monto

        # =================================================
        # 7. ISR (sobre ingresos menos aportes TSS)
        # =================================================

        if usar_isr:
            salario_gravable = max(
                total_ingresos - monto_afp - monto_ars,
                Decimal('0.00')
            )
            monto_isr = calcular_isr(salario_gravable, ppa)

            if monto_isr > 0:
                DescuentoNomina.objects.create(
                    nomina=nomina,
                    tipo=tipo_isr,
                    descripcion='ISR (Impuesto Sobre la Renta)',
                    monto=monto_isr
                )
                total_descuentos += monto_isr

        # =================================================
        # 8. CÁLCULO FINAL
        # =================================================

        neto_pagar = total_ingresos - total_descuentos

        nomina.total_ingresos = total_ingresos
        nomina.total_descuentos = total_descuentos
        nomina.neto_pagar = neto_pagar
        nomina.save()

    # =====================================================
    # MARCAR PERIODO
    # =====================================================

    periodo.nomina_generada = True
    periodo.save()

    return True


# =========================================================
# ANULAR NOMINA
# =========================================================

@transaction.atomic
def anular_nomina(periodo):
    """Elimina la nómina de un período y lo deja listo para regenerar."""
    if periodo.cerrado:
        raise ValidationError("No se puede anular un período cerrado.")

    if Nomina.objects.filter(
        periodo=periodo,
        pagado=True,
    ).exists():
        raise ValidationError(
            "No se puede anular: hay nóminas ya pagadas en este período."
        )

    periodo.nominas.all().delete()

    periodo.nomina_generada = False
    periodo.save()


# =========================================================
# GENERAR PERIODOS AUTOMATICOS
# =========================================================

def generar_periodos_si_no_existen(centro_id):

    config = ConfiguracionCentro.objects.filter(
        centro_id=centro_id
    ).first()

    if config is None:
        return

    hoy = date.today()

    if config.tipo_pago_nomina == 'mensual':
        generar_mensual(centro_id, hoy.year)

    elif config.tipo_pago_nomina == 'quincenal':
        generar_quincenal(centro_id, hoy.year)

    elif config.tipo_pago_nomina == 'semanal':
        generar_semanal(centro_id, hoy.year)


# =========================================================
# PERIODOS MENSUALES
# =========================================================

def generar_mensual(centro_id, anio):

    for mes in range(1, 13):

        inicio = date(anio, mes, 1)

        fin = (
            inicio +
            relativedelta(months=1) -
            timedelta(days=1)
        )

        PeriodoNomina.objects.get_or_create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=1,
            defaults={
                'fecha_inicio': inicio,
                'fecha_fin': fin,
                'fecha_pago': fin,
                'descripcion': f"Mensual {mes}/{anio}",
            }
        )


# =========================================================
# PERIODOS QUINCENALES
# =========================================================

def generar_quincenal(centro_id, anio):

    for mes in range(1, 13):

        PeriodoNomina.objects.get_or_create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=1,
            defaults={
                'fecha_inicio': date(anio, mes, 1),
                'fecha_fin': date(anio, mes, 15),
                'fecha_pago': date(anio, mes, 15),
                'descripcion': f"Quincena 1 {mes}/{anio}",
            }
        )

        ultimo_dia = (
            date(anio, mes, 1) +
            relativedelta(months=1) -
            timedelta(days=1)
        ).day

        PeriodoNomina.objects.get_or_create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=2,
            defaults={
                'fecha_inicio': date(anio, mes, 16),
                'fecha_fin': date(anio, mes, ultimo_dia),
                'fecha_pago': date(anio, mes, ultimo_dia),
                'descripcion': f"Quincena 2 {mes}/{anio}",
            }
        )


# =========================================================
# PERIODOS SEMANALES
# =========================================================

def generar_semanal(centro_id, anio):

    inicio = date(anio, 1, 1)

    for semana in range(1, 54):

        if inicio.year != anio:
            break

        fin = inicio + timedelta(days=6)

        PeriodoNomina.objects.get_or_create(
            centro_id=centro_id,
            anio=anio,
            mes=inicio.month,
            numero_periodo=semana,
            defaults={
                'fecha_inicio': inicio,
                'fecha_fin': fin,
                'fecha_pago': fin,
                'descripcion': f"Semana {semana}/{anio}",
            }
        )

        inicio = fin + timedelta(days=1)


# =========================================================
# CACHÉ DE LISTADOS Y MÉTRICAS
# =========================================================
#
# Estrategia idéntica a caja/facturación: dominio de invalidación
# `nomina:{centro}`. Cuando cambia ConfiguracionNomina, PeriodoNomina,
# Nomina o su detalle de ingresos/descuentos, se incrementa la versión
# y todas las claves del centro quedan invalidadas de forma inmediata.

TTL_NOMINA = 'CACHE_TTL_MEDIO'


def invalidar_nomina_centro(centro_id):
    """Invalida dashboard, historial, detalle de período y boletas de
    un centro cuando cambia su nómina."""
    invalidar_dominio(f'nomina:{centro_id}')


def _version_nomina(centro_id):
    return obtener_version(f'nomina:{centro_id}')


def _nominas_detalle(periodo):
    """Nóminas de un período con relaciones y detalle prefetchados
    (los totales por tipo dependen del detalle de descuentos)."""
    return list(
        periodo.nominas.all()
        .select_related(
            'usuario',
            'configuracion__cargo',
            'configuracion__afp',
            'configuracion__ars',
            'generado_por',
        )
        .prefetch_related('ingresos__tipo', 'descuentos__tipo')
    )


def _totales(nominas):
    """Agregados de un listado de nóminas (excluye ANULADAS)."""
    activas = [n for n in nominas if n.estado != 'ANULADA']
    return {
        'salarios': sum((n.salario_base for n in activas), Decimal('0.00')),
        'ingresos': sum((n.total_ingresos for n in activas), Decimal('0.00')),
        'descuentos': sum(
            (n.total_descuentos for n in activas), Decimal('0.00')
        ),
        'afp': sum((n.monto_afp for n in activas), Decimal('0.00')),
        'ars': sum((n.monto_ars for n in activas), Decimal('0.00')),
        'isr': sum((n.monto_isr for n in activas), Decimal('0.00')),
        'neto': sum((n.neto_pagar for n in activas), Decimal('0.00')),
        'cantidad': len(activas),
    }


def metricas_dashboard(centro):
    """Datos del panel de nómina cacheados por dominio."""
    clave = f'nomina_dashboard:{centro.id}:{_version_nomina(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: _metricas_dashboard_sql(centro),
        version=1,
        timeout=ttl(TTL_NOMINA),
    )


def _metricas_dashboard_sql(centro):
    from django.utils import timezone

    hoy = timezone.localdate()

    config = ConfiguracionCentro.objects.filter(centro=centro).first()

    empleados = list(
        ConfiguracionNomina.objects.filter(
            centro=centro,
            activo_nomina=True,
        ).select_related('usuario', 'cargo', 'afp', 'ars')
    )

    periodo_actual = PeriodoNomina.objects.filter(
        centro=centro,
        anio=hoy.year,
        mes=hoy.month,
    ).first()

    ultima_nomina = (
        PeriodoNomina.objects
        .filter(centro=centro, nomina_generada=True)
        .order_by('-anio', '-mes', '-numero_periodo')
        .first()
    )

    total_ultima = 0
    cantidad_pagados = 0
    if ultima_nomina:
        nominas = _nominas_detalle(ultima_nomina)
        total_ultima = _totales(nominas)['neto']
        cantidad_pagados = len(
            [n for n in nominas if n.estado != 'ANULADA']
        )

    proximos_periodos = list(
        PeriodoNomina.objects
        .filter(centro=centro, nomina_generada=False, cerrado=False)
        .order_by('anio', 'mes', 'numero_periodo')[:6]
    )

    alertas = []
    for emp in empleados:
        if not emp.afp:
            alertas.append(f"{emp.usuario.get_full_name()} no tiene AFP asignada")
        if not emp.ars:
            alertas.append(f"{emp.usuario.get_full_name()} no tiene ARS asignada")
        if not emp.cargo:
            alertas.append(f"{emp.usuario.get_full_name()} no tiene cargo asignado")

    return {
        'config': config,
        'empleados': empleados,
        'cantidad_empleados': len(empleados),
        'periodo_actual': periodo_actual,
        'ultima_nomina': ultima_nomina,
        'total_ultima': total_ultima,
        'cantidad_pagados': cantidad_pagados,
        'proximos_periodos': proximos_periodos,
        'alertas': alertas[:12],
    }


def datos_periodo_detalle(periodo):
    """Nóminas, totales y datos de impresión de un período, cacheados."""
    clave = (
        f'nomina_periodo:{periodo.centro_id}:{periodo.id}:'
        f'{_version_nomina(periodo.centro_id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _datos_periodo_detalle_sql(periodo),
        version=1,
        timeout=ttl(TTL_NOMINA),
    )


def _datos_periodo_detalle_sql(periodo):
    nominas = _nominas_detalle(periodo)
    totales = _totales(nominas)

    datos_impresion = {
        'centro': periodo.centro.nombre,
        'codigo': periodo.centro.codigo_minerd,
        'direccion': periodo.centro.direccion,
        'titulo': periodo.descripcion,
        'fecha_inicio': periodo.fecha_inicio.strftime('%d/%m/%Y'),
        'fecha_fin': periodo.fecha_fin.strftime('%d/%m/%Y'),
        'fecha_pago': periodo.fecha_pago.strftime('%d/%m/%Y'),
        'numero_periodo': periodo.numero_periodo,
        'filas': [
            {
                'nombre': n.usuario.get_full_name() or n.usuario.username,
                'cargo': n.configuracion.cargo.nombre if n.configuracion.cargo else '—',
                'salario': float(n.salario_base),
                'ingresos': float(n.total_ingresos),
                'afp': float(n.monto_afp),
                'ars': float(n.monto_ars),
                'isr': float(n.monto_isr),
                'descuentos': float(n.total_descuentos),
                'neto': float(n.neto_pagar),
            }
            for n in nominas
        ],
    }

    return {
        'nominas': nominas,
        'totales': totales,
        'datos_impresion': datos_impresion,
    }


def historial_nomina(centro):
    """Historial de nóminas por (año, mes) cacheados por dominio."""
    clave = f'nomina_historial:{centro.id}:{_version_nomina(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: _historial_nomina_sql(centro),
        version=1,
        timeout=ttl(TTL_NOMINA),
    )


def _historial_nomina_sql(centro):
    from django.db.models import Count, Q, Sum

    periodos = list(
        PeriodoNomina.objects
        .filter(centro=centro, nomina_generada=True)
        .annotate(
            total_neto=Sum(
                'nominas__neto_pagar',
                filter=Q(nominas__estado__in=ESTADOS_ACTIVOS),
            ),
            cantidad_empleados=Count(
                'nominas',
                filter=Q(nominas__estado__in=ESTADOS_ACTIVOS),
            ),
        )
        .order_by('-anio', '-mes', '-numero_periodo')
    )

    historial = {}
    for periodo in periodos:
        anio = periodo.anio
        mes = MESES.get(periodo.mes, str(periodo.mes))
        historial.setdefault(anio, {}).setdefault(mes, []).append(periodo)

    return historial


def datos_boleta_pago(nomina):
    """Detalle de ingresos y descuentos de una boleta, cacheado."""
    centro_id = nomina.periodo.centro_id
    clave = (
        f'nomina_boleta:{centro_id}:{nomina.id}:'
        f'{_version_nomina(centro_id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _datos_boleta_pago_sql(nomina),
        version=1,
        timeout=ttl(TTL_NOMINA),
    )


def _datos_boleta_pago_sql(nomina):
    return {
        'ingresos': list(
            nomina.ingresos.all().select_related('tipo')
        ),
        'descuentos': list(
            nomina.descuentos.all().select_related('tipo')
        ),
    }


# =========================================================
# NOTIFICACION DE NOMINA POR CORREO
# =========================================================

def enviar_notificaciones_nomina(periodo):
    """Envía a cada empleado un correo con su recibo de pago en PDF.

    Devuelve un dict con la cantidad de correos enviados, empleados sin
    correo registrado y errores. Un fallo al enviar un correo NO aborta
    el envío de los demás ni la generación de la nómina.
    """
    enviados = 0
    sin_correo = 0
    errores = 0

    nominas = (
        periodo.nominas.all()
        .select_related(
            'usuario',
            'configuracion__cargo',
            'periodo__centro',
        )
        .prefetch_related('ingresos', 'descuentos')
    )

    mes = MESES.get(periodo.mes, str(periodo.mes))
    anio = periodo.anio

    for nomina in nominas:
        email = nomina.usuario.email

        if not email:
            sin_correo += 1
            continue

        nombre = nomina.usuario.get_full_name() or nomina.usuario.username

        asunto = f"Recibo de pago · {mes} {anio}"
        mensaje = (
            f"Hola {nombre},\n\n"
            f"Te notificamos que se ha generado tu nómina correspondiente "
            f"al mes de {mes} del año {anio} por un monto de "
            f"RD$ {nomina.neto_pagar:,.2f}.\n\n"
            f"Adjunto encontrarás tu recibo de pago en formato PDF.\n\n"
            f"Gracias."
        )

        try:
            pdf = generar_pdf_boleta(
                nomina,
                list(nomina.ingresos.all()),
                list(nomina.descuentos.all()),
            )
            enviar_email_con_pdf(
                asunto=asunto,
                mensaje=mensaje,
                destinatario=email,
                archivo_nombre=f"recibo_pago_{nomina.id}.pdf",
                pdf_bytes=pdf,
                centro=periodo.centro,
            )
            enviados += 1
        except Exception:
            logger.exception(
                'Error enviando recibo de nómina a %s (%s)',
                email,
                nomina.id,
            )
            errores += 1

    return {
        'enviados': enviados,
        'sin_correo': sin_correo,
        'errores': errores,
    }
