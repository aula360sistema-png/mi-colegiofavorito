from datetime import date

from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.models import CentroEducativo, ConfiguracionCentro

from nomina.models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    DescuentoEmpleado,
    IngresoEmpleado,
    Nomina,
    PeriodoNomina,
    TipoDescuento,
    TipoIngreso,
)
from nomina.services import (
    anular_nomina,
    calcular_isr,
    datos_boleta_pago,
    datos_periodo_detalle,
    factor_periodo,
    generar_mensual,
    generar_nomina,
    generar_periodos_si_no_existen,
    generar_quincenal,
    generar_semanal,
    historial_nomina,
    metricas_dashboard,
    periodos_por_anio,
)
from usuarios.models import Usuario


class BaseNominaTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.admin = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='clave123'
        )
        self.admin.rol = 'superadmin'
        self.admin.save()

        self.empleado = Usuario.objects.create_user(
            username='empleado1',
            email='empleado1@test.com',
            password='clave123'
        )
        self.empleado.rol = 'admin'
        self.empleado.save()

        self.cargo = Cargo.objects.create(
            nombre='Coordinador',
            descripcion='Encargado académico'
        )

        self.afp = AFP.objects.create(
            nombre='AFP Crecer',
            porcentaje_empleado=Decimal('2.87')
        )

        self.ars = ARS.objects.create(
            nombre='ARS Universal',
            porcentaje_empleado=Decimal('3.04')
        )

        self.config = ConfiguracionNomina.objects.create(
            usuario=self.empleado,
            centro=self.centro,
            cargo=self.cargo,
            salario_base=Decimal('50000.00'),
            afp=self.afp,
            ars=self.ars,
            tipo_pago='mensual',
            activo_nomina=True,
        )

        TipoDescuento.objects.create(
            nombre='AFP',
            es_porcentaje=False,
            obligatorio=True,
            activo=True
        )
        TipoDescuento.objects.create(
            nombre='ARS',
            es_porcentaje=False,
            obligatorio=True,
            activo=True
        )

        self.periodo = PeriodoNomina.objects.create(
            centro=self.centro,
            anio=2026,
            mes=6,
            numero_periodo=1,
            descripcion='Mensual 6/2026',
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30),
            fecha_pago=date(2026, 6, 30),
        )

    def crear_periodo(self, **kwargs):
        base = {
            'centro': self.centro,
            'anio': 2026,
            'mes': 6,
            'numero_periodo': 1,
            'descripcion': 'Mensual 6/2026',
            'fecha_inicio': date(2026, 6, 1),
            'fecha_fin': date(2026, 6, 30),
            'fecha_pago': date(2026, 6, 30),
        }
        base.update(kwargs)
        return PeriodoNomina.objects.create(**base)

    def configurar_pago(self, tipo):
        config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            tipo_pago_nomina=tipo,
            modulo_nomina=True
        )
        return config


class NominaServicesTestCase(BaseNominaTestCase):

    # --------------------------------------------------
    # PRORRATEO
    # --------------------------------------------------

    def test_factor_periodo(self):
        self.assertEqual(factor_periodo('mensual'), Decimal('1.00'))
        self.assertEqual(factor_periodo('quincenal'), Decimal('0.50'))
        self.assertEqual(
            factor_periodo('semanal'),
            Decimal('12') / Decimal('52')
        )
        self.assertEqual(factor_periodo(None), Decimal('1.00'))

    def test_periodos_por_anio(self):
        self.assertEqual(periodos_por_anio('mensual'), 12)
        self.assertEqual(periodos_por_anio('quincenal'), 24)
        self.assertEqual(periodos_por_anio('semanal'), 52)

    # --------------------------------------------------
    # ISR
    # --------------------------------------------------

    def test_isr_exento(self):
        self.assertEqual(
            calcular_isr(Decimal('10000.00'), 12),
            Decimal('0.00')
        )

    def test_isr_tramo_15_porciento(self):
        resultado = calcular_isr(Decimal('41666.67'), 12)
        self.assertEqual(resultado, Decimal('1047.25'))

    def test_isr_tramo_20_porciento(self):
        resultado = calcular_isr(Decimal('55000.00'), 12)
        self.assertEqual(resultado, Decimal('3195.88'))

    def test_isr_tramo_25_porciento(self):
        resultado = calcular_isr(Decimal('80000.00'), 12)
        self.assertEqual(resultado, Decimal('8582.95'))

    def test_isr_con_salario_negativo(self):
        self.assertEqual(
            calcular_isr(Decimal('-100.00'), 12),
            Decimal('0.00')
        )

    # --------------------------------------------------
    # GENERAR NOMINA MENSUAL
    # --------------------------------------------------

    def test_generar_nomina_mensual(self):
        self.configurar_pago('mensual')

        IngresoEmpleado.objects.create(
            configuracion=self.config,
            tipo=TipoIngreso.objects.create(
                nombre='Bono de transporte'
            ),
            monto=Decimal('1000.00'),
            activo=True
        )

        DescuentoEmpleado.objects.create(
            configuracion=self.config,
            tipo=TipoDescuento.objects.create(
                nombre='Prestamo',
                es_porcentaje=False
            ),
            monto=Decimal('200.00'),
            activo=True
        )

        generar_nomina(
            self.periodo,
            self.centro.id,
            generado_por=self.admin
        )

        nomina = Nomina.objects.get(periodo=self.periodo)

        self.assertEqual(nomina.salario_base, Decimal('50000.00'))
        self.assertEqual(nomina.total_ingresos, Decimal('51000.00'))
        self.assertEqual(nomina.monto_afp, Decimal('1435.00'))
        self.assertEqual(nomina.monto_ars, Decimal('1520.00'))
        self.assertEqual(nomina.monto_isr, Decimal('2004.00'))
        self.assertEqual(nomina.total_descuentos, Decimal('5159.00'))
        self.assertEqual(nomina.neto_pagar, Decimal('45841.00'))
        self.assertEqual(nomina.generado_por, self.admin)
        self.assertTrue(self.periodo.nomina_generada)

        self.assertEqual(self.periodo.total_ingresos(), Decimal('51000.00'))
        self.assertEqual(self.periodo.total_descuentos(), Decimal('5159.00'))
        self.assertEqual(self.periodo.total_neto(), Decimal('45841.00'))

    def test_generar_nomina_quincenal_prorratea(self):
        self.configurar_pago('quincenal')

        generar_nomina(
            self.periodo,
            self.centro.id,
            generado_por=self.admin
        )

        nomina = Nomina.objects.get(periodo=self.periodo)

        self.assertEqual(nomina.salario_base, Decimal('25000.00'))
        self.assertEqual(nomina.total_ingresos, Decimal('25000.00'))
        self.assertEqual(nomina.monto_afp, Decimal('717.50'))
        self.assertEqual(nomina.monto_ars, Decimal('760.00'))
        self.assertEqual(nomina.monto_isr, Decimal('927.00'))
        self.assertEqual(nomina.total_descuentos, Decimal('2404.50'))
        self.assertEqual(nomina.neto_pagar, Decimal('22595.50'))

    def test_generar_nomina_semanal_prorratea(self):
        self.configurar_pago('semanal')

        generar_nomina(
            self.periodo,
            self.centro.id,
            generado_por=self.admin
        )

        nomina = Nomina.objects.get(periodo=self.periodo)

        self.assertEqual(nomina.salario_base, Decimal('11538.46'))

    def test_isr_desactivado_no_se_calcula(self):
        self.configurar_pago('mensual')

        tipo_isr = TipoDescuento.objects.create(
            nombre='ISR',
            es_porcentaje=False,
            obligatorio=True,
            activo=False
        )

        generar_nomina(
            self.periodo,
            self.centro.id,
            generado_por=self.admin
        )

        nomina = Nomina.objects.get(periodo=self.periodo)

        self.assertEqual(nomina.monto_isr, Decimal('0.00'))
        self.assertFalse(
            nomina.descuentos.filter(tipo=tipo_isr).exists()
        )

    def test_generar_nomina_duplicada_rechazada(self):
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        with self.assertRaises(ValidationError):
            generar_nomina(self.periodo, self.centro.id)

    def test_regenerar_periodo_inconsistente_limpia_previas(self):
        """Un período con nóminas pero nomina_generada=False (estado
        inconsistente) se regenera sin chocar con el unique_together."""
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        anular_nomina(self.periodo)

        nominas_previas = Nomina.objects.filter(
            periodo=self.periodo
        ).count()
        self.assertEqual(nominas_previas, 0)

        generar_nomina(self.periodo, self.centro.id)

        self.assertTrue(self.periodo.nomina_generada)

    def test_regenerar_con_nominas_previas_no_duplica(self):
        """Si quedaron nóminas previas sin flag, la regeneración las
        reemplaza en vez de chocar con el unique_together."""
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        self.periodo.nomina_generada = False
        self.periodo.save()

        generar_nomina(self.periodo, self.centro.id)

        self.assertEqual(
            Nomina.objects.filter(periodo=self.periodo).count(),
            1
        )
        self.assertTrue(self.periodo.nomina_generada)

    def test_generar_nomina_sin_empleados(self):
        self.configurar_pago('mensual')
        self.config.activo_nomina = False
        self.config.save()

        with self.assertRaises(ValidationError):
            generar_nomina(self.periodo, self.centro.id)

    def test_generar_nomina_sin_configuracion_de_centro(self):
        generar_nomina(self.periodo, self.centro.id)
        self.assertTrue(self.periodo.nomina_generada)

    def test_empleado_inactivo_no_se_incluye(self):
        self.configurar_pago('mensual')

        segundo = Usuario.objects.create_user(
            username='empleado2',
            email='empleado2@test.com',
            password='clave123'
        )
        ConfiguracionNomina.objects.create(
            usuario=segundo,
            centro=self.centro,
            salario_base=Decimal('30000.00'),
            activo_nomina=True,
        )

        self.empleado.is_active = False
        self.empleado.save()

        generar_nomina(self.periodo, self.centro.id)

        nominas = Nomina.objects.filter(periodo=self.periodo)
        self.assertEqual(nominas.count(), 1)
        self.assertEqual(nominas.first().usuario, segundo)

    # --------------------------------------------------
    # ANULAR NOMINA
    # --------------------------------------------------

    def test_anular_nomina(self):
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        self.assertTrue(self.periodo.nomina_generada)

        anular_nomina(self.periodo)

        self.assertFalse(Nomina.objects.filter(periodo=self.periodo).exists())
        self.assertFalse(self.periodo.nomina_generada)

    def test_anular_nomina_periodo_cerrado(self):
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        self.periodo.cerrado = True
        self.periodo.save()

        with self.assertRaises(ValidationError):
            anular_nomina(self.periodo)

    def test_anular_nomina_con_pago_realizado(self):
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        Nomina.objects.filter(periodo=self.periodo).update(pagado=True)

        with self.assertRaises(ValidationError):
            anular_nomina(self.periodo)

    # --------------------------------------------------
    # GENERACION DE PERIODOS
    # --------------------------------------------------

    def test_generar_mensual(self):
        generar_mensual(self.centro.id, 2027)

        self.assertEqual(
            PeriodoNomina.objects.filter(
                centro=self.centro,
                anio=2027
            ).count(),
            12
        )

    def test_generar_quincenal(self):
        generar_quincenal(self.centro.id, 2027)

        periodos = PeriodoNomina.objects.filter(
            centro=self.centro,
            anio=2027
        )
        self.assertEqual(periodos.count(), 24)
        self.assertTrue(periodos.filter(numero_periodo=1).exists())
        self.assertTrue(periodos.filter(numero_periodo=2).exists())

    def test_generar_semanal(self):
        generar_semanal(self.centro.id, 2027)

        periodos = PeriodoNomina.objects.filter(
            centro=self.centro,
            anio=2027
        )
        self.assertGreaterEqual(periodos.count(), 52)
        self.assertLessEqual(periodos.count(), 53)

    def test_generar_mensual_idempotente(self):
        generar_mensual(self.centro.id, 2027)
        generar_mensual(self.centro.id, 2027)
        generar_mensual(self.centro.id, 2027)

        self.assertEqual(
            PeriodoNomina.objects.filter(
                centro=self.centro,
                anio=2027
            ).count(),
            12
        )

    def test_generar_quincenal_idempotente(self):
        generar_quincenal(self.centro.id, 2027)
        generar_quincenal(self.centro.id, 2027)

        self.assertEqual(
            PeriodoNomina.objects.filter(
                centro=self.centro,
                anio=2027
            ).count(),
            24
        )

    def test_generar_semanal_idempotente(self):
        generar_semanal(self.centro.id, 2027)
        generar_semanal(self.centro.id, 2027)

        periodos = PeriodoNomina.objects.filter(
            centro=self.centro,
            anio=2027
        )
        self.assertGreaterEqual(periodos.count(), 52)
        self.assertLessEqual(periodos.count(), 53)

    def test_generar_periodos_no_duplica_existentes(self):
        ConfiguracionCentro.objects.create(
            centro=self.centro,
            tipo_pago_nomina='mensual',
        )

        generar_periodos_si_no_existen(self.centro.id)
        generar_periodos_si_no_existen(self.centro.id)

        total = PeriodoNomina.objects.filter(
            centro=self.centro,
            anio=2026,
        ).count()
        self.assertEqual(total, 12)

    def test_periodo_unico_por_centro_mes_numero(self):
        from django.db.utils import IntegrityError

        crear = lambda **kwargs: PeriodoNomina.objects.create(
            centro=self.centro,
            anio=2027,
            mes=1,
            numero_periodo=1,
            descripcion='Mensual 1/2027',
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 1, 31),
            fecha_pago=date(2027, 1, 31),
        )
        crear()

        with self.assertRaises(IntegrityError):
            crear()

    # --------------------------------------------------
    # VISTAS (smoke test)
    # --------------------------------------------------

    def test_dashboard_requiere_rol_nomina(self):
        self.client.login(username='admin', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        response = self.client.get('/nomina/')

        self.assertEqual(response.status_code, 200)

        response = self.client.get('/nomina/periodos/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f'/nomina/periodos/{self.periodo.id}/'
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f'/nomina/empleado/{self.config.pk}/'
        )
        self.assertEqual(response.status_code, 200)

    def test_detalle_periodo_muestra_documento_impreso(self):
        from nomina.services import generar_nomina

        self.client.login(username='admin', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id)

        response = self.client.get(
            f'/nomina/periodos/{self.periodo.id}/'
        )

        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode('utf-8')

        self.assertIn('datos-impresion', contenido)
        self.assertIn('imprimirNomina', contenido)
        self.assertIn('TOTALES', contenido)


class CacheNominaTests(BaseNominaTestCase):

    def setUp(self):
        cache.clear()
        super().setUp()
        self.configurar_pago('mensual')
        generar_nomina(self.periodo, self.centro.id, generado_por=self.admin)

    def test_metricas_dashboard_segunda_llamada_sin_consultas(self):
        primera = metricas_dashboard(self.centro)
        self.assertEqual(primera['cantidad_empleados'], 1)
        self.assertGreater(primera['total_ultima'], 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = metricas_dashboard(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda['total_ultima'], primera['total_ultima'])

    def test_datos_periodo_detalle_segunda_llamada_sin_consultas(self):
        primera = datos_periodo_detalle(self.periodo)
        self.assertEqual(primera['totales']['cantidad'], 1)
        self.assertGreater(len(primera['nominas']), 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = datos_periodo_detalle(self.periodo)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda['nominas']), 1)

    def test_historial_segunda_llamada_sin_consultas(self):
        primera = historial_nomina(self.centro)
        self.assertIn(2026, primera)

        with CaptureQueriesContext(connection) as ctx:
            segunda = historial_nomina(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertIn(2026, segunda)

    def test_boleta_segunda_llamada_sin_consultas(self):
        nomina = Nomina.objects.get(periodo=self.periodo)
        primera = datos_boleta_pago(nomina)
        self.assertGreater(len(primera['ingresos']), 0)
        self.assertGreater(len(primera['descuentos']), 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = datos_boleta_pago(nomina)
        self.assertEqual(len(ctx), 0)

    def test_cambio_de_estado_invalida_metricas(self):
        antes = metricas_dashboard(self.centro)
        self.assertEqual(antes['cantidad_pagados'], 1)

        nomina = Nomina.objects.get(periodo=self.periodo)
        nomina.estado = 'ANULADA'
        nomina.save()

        despues = metricas_dashboard(self.centro)
        self.assertEqual(despues['cantidad_pagados'], 0)

    def test_cambio_de_estado_invalida_periodo_detalle(self):
        antes = datos_periodo_detalle(self.periodo)
        self.assertEqual(antes['totales']['cantidad'], 1)

        nomina = Nomina.objects.get(periodo=self.periodo)
        nomina.estado = 'ANULADA'
        nomina.save()

        despues = datos_periodo_detalle(self.periodo)
        self.assertEqual(despues['totales']['cantidad'], 0)
