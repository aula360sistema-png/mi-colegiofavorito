from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from core.models import ConfiguracionCentro

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


# =========================================================
# GENERAR NOMINA ERP
# =========================================================

@transaction.atomic
def generar_nomina(periodo, centro_id):

    """
    Motor ERP básico de nómina
    """

    print(
        f"Generando nómina para período: "
        f"{periodo} - Centro ID: {centro_id}"
    )

    # =====================================================
    # VALIDAR DUPLICADO
    # =====================================================

    if periodo.nomina_generada:

        raise ValidationError(
            "La nómina de este período ya fue generada."
        )

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

    # =====================================================
    # TIPOS NECESARIOS
    # =====================================================

    tipo_salario_base = TipoIngreso.objects.filter(
        nombre__iexact='Salario Base'
    ).first()

    if not tipo_salario_base:

        raise ValidationError(
            "No existe el TipoIngreso 'Salario Base'"
        )

    # =====================================================
    # DESCUENTOS GLOBALES
    # =====================================================

    descuentos_globales = TipoDescuento.objects.filter(
        activo=True,
        obligatorio=True
    )

    # =====================================================
    # LOOP PRINCIPAL
    # =====================================================

    for emp in empleados:

        salario_base = emp.salario_base or Decimal("0.00")

        total_ingresos = Decimal("0.00")
        total_descuentos = Decimal("0.00")

        # =================================================
        # CREAR NOMINA
        # =================================================

        nomina = Nomina.objects.create(
            periodo=periodo,
            usuario=emp.usuario,
            configuracion=emp,
            salario_base=salario_base,
            total_ingresos=0,
            total_descuentos=0,
            neto_pagar=0,
            pagado=False
        )

        # =================================================
        # 1. SALARIO BASE
        # =================================================

        IngresoNomina.objects.create(
            nomina=nomina,
            tipo=tipo_salario_base,
            descripcion='Salario Base',
            monto=salario_base
        )

        total_ingresos += salario_base

        # =================================================
        # 2. INGRESOS EXTRA
        # =================================================

        ingresos = IngresoEmpleado.objects.filter(
            configuracion=emp,
            activo=True
        ).select_related('tipo')

        for ingreso in ingresos:

            IngresoNomina.objects.create(
                nomina=nomina,
                tipo=ingreso.tipo,
                descripcion=ingreso.tipo.nombre,
                monto=ingreso.monto
            )

            total_ingresos += ingreso.monto

        # =================================================
        # 3. AFP
        # =================================================

        if emp.afp:

            monto_afp = (
                salario_base *
                emp.afp.porcentaje_empleado
            ) / Decimal("100")

            tipo_afp = TipoDescuento.objects.filter(
                nombre__iexact='AFP'
            ).first()

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

        if emp.ars:

            monto_ars = (
                salario_base *
                emp.ars.porcentaje_empleado
            ) / Decimal("100")

            tipo_ars = TipoDescuento.objects.filter(
                nombre__iexact='ARS'
            ).first()

            if tipo_ars:

                DescuentoNomina.objects.create(
                    nomina=nomina,
                    tipo=tipo_ars,
                    descripcion=f'ARS {emp.ars.nombre}',
                    monto=monto_ars
                )

                total_descuentos += monto_ars

        # =================================================
        # 5. DESCUENTOS GLOBALES
        # =================================================

        for descuento in descuentos_globales:

            if descuento.nombre.upper() in ['AFP', 'ARS']:
                continue

            monto_descuento = Decimal("0.00")

            if descuento.es_porcentaje:

                monto_descuento = (
                    salario_base *
                    descuento.porcentaje
                ) / Decimal("100")

            else:

                monto_descuento = descuento.porcentaje

            if monto_descuento <= 0:
                continue

            DescuentoNomina.objects.create(
                nomina=nomina,
                tipo=descuento,
                descripcion=descuento.nombre,
                monto=monto_descuento
            )

            total_descuentos += monto_descuento

        # =================================================
        # 6. DESCUENTOS PERSONALIZADOS
        # =================================================

        descuentos_personales = DescuentoEmpleado.objects.filter(
            configuracion=emp,
            activo=True
        ).select_related('tipo')

        for descuento in descuentos_personales:

            DescuentoNomina.objects.create(
                nomina=nomina,
                tipo=descuento.tipo,
                descripcion=descuento.tipo.nombre,
                monto=descuento.monto
            )

            total_descuentos += descuento.monto

        # =================================================
        # 7. CALCULO FINAL
        # =================================================

        neto_pagar = (
            total_ingresos -
            total_descuentos
        )

        # =================================================
        # 8. ACTUALIZAR NOMINA
        # =================================================

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
# GENERAR PERIODOS AUTOMATICOS
# =========================================================

def generar_periodos_si_no_existen(centro_id):

    config = ConfiguracionCentro.objects.get(
        centro_id=centro_id
    )

    hoy = date.today()

    anio = hoy.year

    existentes = PeriodoNomina.objects.filter(
        centro_id=centro_id,
        anio=anio
    ).exists()

    if existentes:
        return

    if config.tipo_pago_nomina == 'mensual':

        generar_mensual(
            centro_id,
            anio
        )

    elif config.tipo_pago_nomina == 'quincenal':

        generar_quincenal(
            centro_id,
            anio
        )

    elif config.tipo_pago_nomina == 'semanal':

        generar_semanal(
            centro_id,
            anio
        )


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

        PeriodoNomina.objects.create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=1,
            fecha_inicio=inicio,
            fecha_fin=fin,
            fecha_pago=fin,
            descripcion=f"Mensual {mes}/{anio}"
        )


# =========================================================
# PERIODOS QUINCENALES
# =========================================================

def generar_quincenal(centro_id, anio):

    for mes in range(1, 13):

        PeriodoNomina.objects.create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=1,
            fecha_inicio=date(anio, mes, 1),
            fecha_fin=date(anio, mes, 15),
            fecha_pago=date(anio, mes, 15),
            descripcion=f"Q1 {mes}/{anio}"
        )

        ultimo_dia = (
            date(anio, mes, 1) +
            relativedelta(months=1) -
            timedelta(days=1)
        ).day

        PeriodoNomina.objects.create(
            centro_id=centro_id,
            anio=anio,
            mes=mes,
            numero_periodo=2,
            fecha_inicio=date(anio, mes, 16),
            fecha_fin=date(anio, mes, ultimo_dia),
            fecha_pago=date(anio, mes, ultimo_dia),
            descripcion=f"Q2 {mes}/{anio}"
        )


# =========================================================
# PERIODOS SEMANALES
# =========================================================

def generar_semanal(centro_id, anio):

    inicio = date(anio, 1, 1)

    for semana in range(1, 53):

        fin = inicio + timedelta(days=6)

        PeriodoNomina.objects.create(
            centro_id=centro_id,
            anio=anio,
            mes=inicio.month,
            numero_periodo=semana,
            fecha_inicio=inicio,
            fecha_fin=fin,
            fecha_pago=fin,
            descripcion=f"Semana {semana}/{anio}"
        )

        inicio = fin + timedelta(days=1)