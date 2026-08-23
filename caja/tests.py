from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from caja.models import AsignacionConcepto, ConceptoPago, Pago
from caja.services import (
    balance_por_concepto,
    calcular_cuentas_por_cobrar,
    deuda_detalle_estudiante,
    pagos_del_centro,
    tiene_deuda_pendiente,
)
from core.cache_utils import borrar, invalidar_dominio
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import Estudiante
from usuarios.models import Usuario


class BaseCajaCacheTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )
        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_caja=True,
        )
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )
        self.usuario = Usuario.objects.create_user(
            username='director1',
            email='director@test.com',
            password='clave123',
        )
        self.usuario.rol = 'director'
        self.usuario.save()

        usuario_alumno = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='clave123',
        )
        usuario_alumno.rol = 'estudiante'
        usuario_alumno.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario_alumno,
            centro=self.centro,
            matricula='MAT-0001',
            primer_nombre='Juan',
            primer_apellido='Pérez',
            sexo='M',
            fecha_nacimiento=date(2010, 1, 1),
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='María Pérez',
            cedula_tutor='00000000000',
            telefono_tutor='8090000000',
            parentesco_tutor='Madre',
        )

        self.concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
        )

        self.pago = Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('5000.00'),
            recibo=1,
            fecha=date(2026, 2, 1),
            creado_por=self.usuario,
        )


class CachePagosDelCentroTests(BaseCajaCacheTestCase):

    def test_segunda_llamada_sin_consultas(self):
        borrar(f'pagos:{self.centro.id}:', version=1)

        primera = pagos_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = pagos_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0].id, self.pago.id)

    def test_pago_nuevo_invalida_cache(self):
        pagos_del_centro(self.centro)

        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('3000.00'),
            recibo=2,
            fecha=date(2026, 3, 1),
            creado_por=self.usuario,
        )

        pagos = pagos_del_centro(self.centro)
        self.assertEqual(len(pagos), 2)


class CacheBalanceTests(BaseCajaCacheTestCase):

    def setUp(self):
        super().setUp()
        self.asignacion = AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )

    def test_balance_cacheado_sin_consultas(self):
        borrar(f'balance:{self.centro.id}:{self.estudiante.id}:{self.anio.id}:', version=1)

        primera = balance_por_concepto(self.centro, self.estudiante, self.anio)
        self.assertGreater(len(primera), 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = balance_por_concepto(self.centro, self.estudiante, self.anio)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0]['pagado'], Decimal('5000.00'))


class CacheCuentasPorCobrarTests(BaseCajaCacheTestCase):

    def setUp(self):
        super().setUp()
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )
        self.concepto_pendiente = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Inscripción',
            monto=Decimal('2500.00'),
        )
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto_pendiente,
            anio_escolar=self.anio,
            activo=True,
        )

    def test_cuentas_por_cobrar_cacheadas_sin_consultas(self):
        borrar(f'cxc:{self.centro.id}:{self.anio.id}:', version=1)

        primera = calcular_cuentas_por_cobrar(self.centro, self.anio)
        self.assertGreater(len(primera), 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = calcular_cuentas_por_cobrar(self.centro, self.anio)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0]['estudiante'].id, self.estudiante.id)

    def test_invalidar_dominio_pagos_refresca(self):
        borrar(f'cxc:{self.centro.id}:{self.anio.id}:', version=1)

        calcular_cuentas_por_cobrar(self.centro, self.anio)

        invalidar_dominio(f'pagos:{self.centro.id}')

        segunda = calcular_cuentas_por_cobrar(self.centro, self.anio)
        self.assertEqual(len(segunda), 1)


class CajaViewsTests(BaseCajaCacheTestCase):

    def login_director(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def setUp(self):
        super().setUp()
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )
        self.login_director()

    def test_caja_inicio_200(self):
        response = self.client.get(reverse('caja:caja_inicio'))
        self.assertEqual(response.status_code, 200)

    def test_lista_pagos_200_con_filtros(self):
        response = self.client.get(reverse('caja:lista_pagos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pérez')

        response = self.client.get(
            reverse('caja:lista_pagos'), {'q': 'Pérez'}
        )
        self.assertEqual(response.status_code, 200)

    def test_lista_egresos_200(self):
        response = self.client.get(reverse('caja:lista_egresos'))
        self.assertEqual(response.status_code, 200)

    def test_reporte_diario_200(self):
        response = self.client.get(reverse('caja:reporte_diario'))
        self.assertEqual(response.status_code, 200)

    def test_cuentas_por_cobrar_200(self):
        response = self.client.get(reverse('caja:cuentas_por_cobrar'))
        self.assertEqual(response.status_code, 200)


HOY_FIJO = date(2026, 8, 15)


class DeudaEstudianteTests(TestCase):

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0003'
        )

        ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_caja=True,
        )

        usuario_alumno = Usuario.objects.create_user(
            username='alumno_deuda',
            email='deuda@test.com',
            password='clave123',
        )
        usuario_alumno.rol = 'estudiante'
        usuario_alumno.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario_alumno,
            centro=self.centro,
            matricula='MAT-DEUDA',
            primer_nombre='Ana',
            primer_apellido='Rojas',
            sexo='F',
            fecha_nacimiento=date(2010, 1, 1),
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 3',
            nombre_tutor='Tutor',
            cedula_tutor='00000000000',
            telefono_tutor='8090000000',
            parentesco_tutor='Madre',
        )

    def _anio(self, fecha_inicio):
        return AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=fecha_inicio,
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

    def _asignar(self, anio, concepto):
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=concepto,
            anio_escolar=anio,
            activo=True,
        )

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_sin_asignaciones_no_hay_deuda(self, _hoy):
        anio = self._anio(date(2026, 6, 1))

        self.assertFalse(tiene_deuda_pendiente(self.centro, self.estudiante, anio))
        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)
        self.assertEqual(detalle['saldo_total'], 0)
        self.assertEqual(detalle['vencida'], 0)
        self.assertEqual(detalle['proxima'], 0)

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_cuota_del_mes_es_proxima_a_vencer(self, _hoy):
        anio = self._anio(date(2026, 8, 1))
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )
        self._asignar(anio, concepto)

        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)

        self.assertTrue(detalle['tiene_deuda'])
        self.assertEqual(detalle['vencida'], 0)
        self.assertEqual(detalle['proxima'], Decimal('5000.00'))
        self.assertEqual(detalle['saldo_total'], Decimal('5000.00'))

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_meses_anteriores_son_vencidos(self, _hoy):
        anio = self._anio(date(2026, 6, 1))
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )
        self._asignar(anio, concepto)

        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)

        # Junio y julio vencidos; agosto próximo a vencer.
        self.assertEqual(detalle['vencida'], Decimal('10000.00'))
        self.assertEqual(detalle['proxima'], Decimal('5000.00'))
        self.assertEqual(detalle['saldo_total'], Decimal('15000.00'))

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_abono_parcial_deja_cuotas_pendientes(self, _hoy):
        anio = self._anio(date(2026, 6, 1))
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )
        self._asignar(anio, concepto)
        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=concepto,
            monto=Decimal('5000.00'),
            recibo=1,
            fecha=HOY_FIJO,
        )

        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)

        # Junio pagado; julio vencido; agosto próximo a vencer.
        self.assertEqual(detalle['vencida'], Decimal('5000.00'))
        self.assertEqual(detalle['proxima'], Decimal('5000.00'))
        self.assertEqual(detalle['saldo_total'], Decimal('10000.00'))

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_no_recurrente_pendiente_es_vencida(self, _hoy):
        anio = self._anio(date(2026, 8, 1))
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Inscripción',
            monto=Decimal('3000.00'),
            es_recurrente=False,
        )
        self._asignar(anio, concepto)

        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)

        self.assertEqual(detalle['vencida'], Decimal('3000.00'))
        self.assertEqual(detalle['proxima'], 0)
        self.assertEqual(detalle['saldo_total'], Decimal('3000.00'))

    @patch('django.utils.timezone.localdate', return_value=HOY_FIJO)
    def test_concepto_pagado_no_genera_deuda(self, _hoy):
        anio = self._anio(date(2026, 8, 1))
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Inscripción',
            monto=Decimal('3000.00'),
            es_recurrente=False,
        )
        self._asignar(anio, concepto)
        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=concepto,
            monto=Decimal('3000.00'),
            recibo=1,
            fecha=HOY_FIJO,
        )

        detalle = deuda_detalle_estudiante(self.centro, self.estudiante, anio)

        self.assertFalse(detalle['tiene_deuda'])
        self.assertEqual(detalle['saldo_total'], 0)
