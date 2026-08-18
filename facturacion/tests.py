from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from caja.forms import PagoForm
from caja.models import ConceptoPago, Pago
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import Estudiante
from facturacion.models import (
    Factura,
    FacturaItem,
    SecuenciaNCF,
    TipoComprobante,
)
from facturacion.services import (
    emitir_factura,
    facturas_del_centro,
    siguiente_ncf,
    tipo_comprobante_predeterminado,
)
from usuarios.models import Usuario


class BaseFacturacionTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            permitir_facturacion=True,
            facturacion_itbis=True,
            rnc='1-30-00000-0',
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

    def login_director(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()


class SecuenciaNCFTests(BaseFacturacionTestCase):

    def test_tipo_predeterminado_es_consumo(self):
        tipo = tipo_comprobante_predeterminado(self.centro)
        self.assertEqual(tipo.codigo, '32')

    def test_siguiente_ncf_secuencial(self):
        tipo = TipoComprobante.objects.get(codigo='32')
        self.assertEqual(siguiente_ncf(self.centro, tipo), 'E320000000001')
        self.assertEqual(siguiente_ncf(self.centro, tipo), 'E320000000002')
        sec = SecuenciaNCF.objects.get(centro=self.centro, tipo=tipo)
        self.assertEqual(sec.ultimo_numero, 2)

    def test_secuencia_independiente_por_tipo(self):
        consumo = TipoComprobante.objects.get(codigo='32')
        credito = TipoComprobante.objects.get(codigo='31')
        self.assertEqual(siguiente_ncf(self.centro, consumo), 'E320000000001')
        self.assertEqual(siguiente_ncf(self.centro, credito), 'E310000000001')


class EmitirFacturaTests(BaseFacturacionTestCase):

    def test_emitir_factura_sin_itbis(self):
        factura = emitir_factura(self.pago, aplicar_itbis=False)
        self.assertEqual(factura.subtotal, Decimal('5000.00'))
        self.assertEqual(factura.itbis, Decimal('0.00'))
        self.assertEqual(factura.total, Decimal('5000.00'))
        self.assertFalse(factura.aplica_itbis)
        self.assertTrue(factura.ncf.startswith('E'))
        self.assertEqual(factura.pago, self.pago)
        self.assertEqual(factura.items.count(), 1)
        item = factura.items.first()
        self.assertEqual(item.descripcion, 'Mensualidad')
        self.assertEqual(item.subtotal, Decimal('5000.00'))

    def test_emitir_factura_con_itbis(self):
        factura = emitir_factura(self.pago, aplicar_itbis=True)
        self.assertEqual(factura.subtotal, Decimal('5000.00'))
        self.assertEqual(factura.itbis, Decimal('900.00'))
        self.assertEqual(factura.total, Decimal('5900.00'))
        self.assertTrue(factura.aplica_itbis)

    def test_emitir_factura_idempotente(self):
        primera = emitir_factura(self.pago, aplicar_itbis=True)
        segunda = emitir_factura(self.pago, aplicar_itbis=False)
        self.assertEqual(primera.id, segunda.id)
        self.assertEqual(Factura.objects.count(), 1)
        sec = SecuenciaNCF.objects.get(
            centro=self.centro,
            tipo=TipoComprobante.objects.get(codigo='32'),
        )
        self.assertEqual(sec.ultimo_numero, 1)

    def test_dos_pagos_generan_ncf_consecutivos(self):
        segundo = Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('3000.00'),
            recibo=2,
            fecha=date(2026, 3, 1),
            creado_por=self.usuario,
        )
        f1 = emitir_factura(self.pago, aplicar_itbis=False)
        f2 = emitir_factura(segundo, aplicar_itbis=False)
        self.assertEqual(f1.ncf, 'E320000000001')
        self.assertEqual(f2.ncf, 'E320000000002')

    def test_emitir_sin_tipos_activos_genera_sin_ncf(self):
        TipoComprobante.objects.update(activo=False)
        factura = emitir_factura(self.pago, aplicar_itbis=False)
        self.assertEqual(factura.ncf, '')
        self.assertIsNone(factura.tipo)


class FacturaViewsTests(BaseFacturacionTestCase):

    def test_facturacion_inicio_200(self):
        emitir_factura(self.pago, aplicar_itbis=True)
        self.login_director()
        response = self.client.get(reverse('facturacion:facturacion_inicio'))
        self.assertEqual(response.status_code, 200)

    def test_lista_facturas_200_y_filtros(self):
        emitir_factura(self.pago, aplicar_itbis=True)
        self.login_director()
        response = self.client.get(reverse('facturacion:lista_facturas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E320000000001')

        response = self.client.get(
            reverse('facturacion:lista_facturas'), {'q': 'Pérez'}
        )
        self.assertEqual(response.status_code, 200)

    def test_detalle_factura_200(self):
        factura = emitir_factura(self.pago, aplicar_itbis=True)
        self.login_director()
        response = self.client.get(
            reverse('facturacion:detalle_factura', args=[factura.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, factura.ncf)

    def test_lista_comprobantes_200_y_toggle(self):
        self.login_director()
        response = self.client.get(reverse('facturacion:lista_comprobantes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '32 · Factura de Consumo Electrónica')

        tipo = TipoComprobante.objects.get(codigo='32')
        response = self.client.post(
            reverse('facturacion:lista_comprobantes'),
            {'tipo_id': tipo.id},
        )
        self.assertEqual(response.status_code, 302)
        tipo.refresh_from_db()
        self.assertFalse(tipo.activo)

    def test_roles_sin_permiso_403(self):
        usuario = Usuario.objects.create_user(
            username='estudiante1',
            email='est@test.com',
            password='clave123',
        )
        usuario.rol = 'estudiante'
        usuario.save()
        self.client.force_login(usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('facturacion:lista_facturas'))
        self.assertEqual(response.status_code, 403)

    def test_secretaria_puede_ver_facturacion(self):
        usuario = Usuario.objects.create_user(
            username='secretaria1',
            email='sec@test.com',
            password='clave123',
        )
        usuario.rol = 'secretaria'
        usuario.save()
        self.client.force_login(usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('facturacion:lista_facturas'))
        self.assertEqual(response.status_code, 200)


class PagoFormFacturacionTests(BaseFacturacionTestCase):

    def test_form_campos_actuales_presentes(self):
        form = PagoForm(centro=self.centro)
        for campo in ['estudiante', 'concepto', 'monto', 'metodo_pago', 'fecha', 'voucher']:
            self.assertIn(campo, form.fields)

    def test_form_no_agrega_campos_de_facturacion(self):
        form = PagoForm(centro=self.centro)
        self.assertNotIn('emitir_factura', form.fields)
        self.assertNotIn('aplica_itbis', form.fields)

    def test_form_sin_facturacion_no_agrega_campos(self):
        self.config.permitir_facturacion = False
        self.config.save()
        form = PagoForm(centro=self.centro)
        self.assertNotIn('emitir_factura', form.fields)
        self.assertNotIn('aplica_itbis', form.fields)


class CacheFacturasDelCentroTests(BaseFacturacionTestCase):

    def setUp(self):
        super().setUp()
        emitir_factura(self.pago, aplicar_itbis=True)

    def test_segunda_llamada_sin_consultas(self):
        from core.cache_utils import borrar
        borrar(f'facturas_lista:{self.centro.id}:', version=1)

        primera = facturas_del_centro(self.centro)
        self.assertGreater(len(primera), 0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = facturas_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0].id, self.pago.factura.id)


class ConfiguracionCentroFormTests(BaseFacturacionTestCase):

    def test_campos_de_facturacion_presentes(self):
        from core.forms import ConfiguracionCentroForm
        form = ConfiguracionCentroForm(instance=self.config)
        self.assertIn('permitir_facturacion', form.fields)
        self.assertIn('rnc', form.fields)
        self.assertIn('facturacion_itbis', form.fields)
