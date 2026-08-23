"""Matriz de independencia entre módulos (planes de venta).

Verifica que un centro sin los módulos de caja/facturación contratados
puede operar todos sus flujos restantes sin deudas huérfanas ni errores:
cada módulo es independiente y los flujos compuestos se degradan solos.
"""

from datetime import date

from django.contrib import messages as dj_messages
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from caja.models import AsignacionConcepto, ConceptoPago
from core.models import (
    AnioEscolar,
    CentroEducativo,
    ConfiguracionCentro,
)
from core.services import modulo_activo
from estudiantes.models import Estudiante, SolicitudCertificado
from tutores.models import Tutor
from usuarios.models import Usuario


class BasePlanTestCase(TestCase):

    def _crear_centro(self, codigo='MIN-9001', **flags_config):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Plan',
            codigo_minerd=codigo,
        )
        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            **flags_config,
        )
        return self.centro

    def _crear_usuario(self, username, rol):
        usuario = Usuario.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='clave123',
        )
        usuario.rol = rol
        usuario.save()
        return usuario

    def _login_con_centro(self, usuario):
        self.client.login(
            username=usuario.username, password='clave123'
        )
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()


class ModuloActivoServicioTests(BasePlanTestCase):

    def setUp(self):
        cache.clear()
        self._crear_centro()

    def test_flag_desconocido_devuelve_false(self):
        self.assertFalse(modulo_activo(self.centro.id, 'inexistente'))

    def test_centro_inexistente_devuelve_false(self):
        self.assertFalse(modulo_activo(None, 'caja'))
        self.assertFalse(modulo_activo(999999, 'caja'))

    def test_refleja_el_flag_del_centro(self):
        self.assertFalse(modulo_activo(self.centro.id, 'caja'))
        self.config.modulo_caja = True
        self.config.save()
        cache.clear()
        self.assertTrue(modulo_activo(self.centro.id, 'caja'))


class PlanSinCajaTests(BasePlanTestCase):
    """Plan sin caja ni facturación: nada se rompe, nada genera deuda."""

    def setUp(self):
        cache.clear()
        self._crear_centro(modulo_certificados=True)

        self.director = self._crear_usuario('dirplan', 'director')

        usuario_estudiante = self._crear_usuario('estplan', 'estudiante')
        self.estudiante = Estudiante.objects.create(
            usuario=usuario_estudiante,
            centro=self.centro,
            matricula='20990001',
            primer_nombre='Ana',
            primer_apellido='Reyes',
            sexo='F',
            fecha_nacimiento='2011-01-15',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor',
            cedula_tutor='00100000001',
            telefono_tutor='809-555-0001',
            parentesco_tutor='Madre',
        )

    # --- Gate de URLs -------------------------------------------------

    def test_urls_de_caja_redirigen_con_aviso(self):
        self._login_con_centro(self.director)

        response = self.client.get(reverse('caja:caja_inicio'), follow=True)

        # home('/') rebotará al dashboard del director: la cadena completa
        # caja -> home -> dashboard confirma que el gate cortó el acceso.
        self.assertRedirects(
            response, reverse('administracion:dashboard_admin')
        )
        mensajes = [str(m) for m in dj_messages.get_messages(response.wsgi_request)]
        self.assertTrue(
            any('caja no está activo' in m for m in mensajes),
            mensajes,
        )

    def test_urls_de_facturacion_redirigen_con_aviso(self):
        self._login_con_centro(self.director)

        response = self.client.get(
            reverse('facturacion:facturacion_inicio'), follow=True
        )

        self.assertRedirects(
            response, reverse('administracion:dashboard_admin')
        )
        mensajes = [str(m) for m in dj_messages.get_messages(response.wsgi_request)]
        self.assertTrue(
            any('facturación no está activo' in m for m in mensajes),
            mensajes,
        )

    def test_home_de_cajero_sin_caja_cierra_sesion_con_aviso(self):
        cajero = self._crear_usuario('cajeroplan', 'cajero')
        self._login_con_centro(cajero)

        response = self.client.get(reverse('core:home'), follow=True)

        self.assertRedirects(response, reverse('usuarios:login'))
        self.assertTrue(any(
            'caja no está activo' in str(m)
            for m in dj_messages.get_messages(response.wsgi_request)
        ))

    # --- Servicios neutrales ------------------------------------------

    def test_deuda_es_neutral_aun_con_asignacion_impaga(self):
        anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )
        concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Inscripción',
            monto=5000,
            es_recurrente=False,
            activo=True,
        )
        AsignacionConcepto.objects.create(
            centro=self.centro,
            concepto=concepto,
            estudiante=self.estudiante,
            anio_escolar=anio,
        )

        from caja.services import (
            balance_por_concepto,
            tiene_deuda_pendiente,
        )

        self.assertFalse(
            tiene_deuda_pendiente(self.centro, self.estudiante, anio)
        )
        self.assertEqual(
            balance_por_concepto(self.centro, self.estudiante, anio),
            [],
        )

    def test_constancia_no_se_bloquea_por_deuda_inexistente(self):
        from caja.services import tiene_deuda_pendiente

        self._login_con_centro(self.director)

        response = self.client.get(
            reverse('constancia_estudiante', args=[self.estudiante.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            tiene_deuda_pendiente(self.centro, self.estudiante)
        )

    # --- Certificados gratuitos ---------------------------------------

    def _solicitar_como_estudiante(self):
        self._login_con_centro(self.estudiante.usuario)
        return self.client.post(
            '/estudiantes/inicio/solicitudes/',
            {
                'tipo_certificado': 'constancia_estudio',
                'metodo_pago': 'efectivo',
                'motivo': 'Trámite',
            },
            follow=True,
        )

    def test_solicitud_del_estudiante_es_gratuita_y_aprobada(self):
        response = self._solicitar_como_estudiante()

        solicitud = SolicitudCertificado.objects.get(
            estudiante=self.estudiante
        )
        self.assertEqual(solicitud.monto, 0)
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertTrue(solicitud.pagado)
        self.assertIsNotNone(solicitud.aprobado_en)

        contenido = response.content.decode('utf-8')
        self.assertIn('Gratuito', contenido)
        self.assertNotIn('Pagar en línea', contenido)

    def test_pago_online_rechazado_para_solicitudes_gratuitas(self):
        self._solicitar_como_estudiante()
        solicitud = SolicitudCertificado.objects.get(
            estudiante=self.estudiante
        )

        self._login_con_centro(self.estudiante.usuario)
        response = self.client.post(
            reverse('estudiante_solicitud_pagar', args=[solicitud.pk]),
            follow=True,
        )

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertTrue(any(
            'no requiere pago' in str(m)
            for m in dj_messages.get_messages(response.wsgi_request)
        ))

    def test_panel_no_ofrece_cobro_pero_si_entrega(self):
        self._solicitar_como_estudiante()
        solicitud = SolicitudCertificado.objects.get(
            estudiante=self.estudiante
        )

        self._login_con_centro(self.director)

        listado = self.client.get(reverse('solicitudes_certificados'))
        contenido = listado.content.decode('utf-8')
        self.assertNotIn('Cobrar en caja', contenido)
        self.assertIn('Exenta', contenido)

        entrega = self.client.post(
            reverse('solicitud_entregar', args=[solicitud.pk]),
            follow=True,
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'entregada')
        self.assertContains(entrega, 'entregado')

    def test_cobro_manual_se_bloquea_sin_caja(self):
        solicitud = SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.estudiante.usuario,
            tipo_certificado='record_notas',
            monto=0,
            estado='aprobada',
            pagado=True,
        )

        self._login_con_centro(self.director)
        response = self.client.post(
            reverse('solicitud_cobrar', args=[solicitud.pk]),
            {'referencia_pago': ''},
            follow=True,
        )

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertTrue(any(
            'gratuitos' in str(m).lower()
            for m in dj_messages.get_messages(response.wsgi_request)
        ))

    # --- Portales sin secciones de dinero ------------------------------

    def test_tutor_inicio_oculta_deudas_sin_caja(self):
        usuario_tutor = self._crear_usuario('tutorplan', 'tutor')
        tutor = Tutor.objects.create(
            usuario=usuario_tutor,
            centro=self.centro,
            cedula='00100000099',
            primer_nombre='Mario',
            primer_apellido='Peña',
            sexo='M',
            fecha_nacimiento=date(1985, 5, 20),
        )
        tutor.estudiantes.add(self.estudiante)

        self._login_con_centro(usuario_tutor)
        response = self.client.get(reverse('tutores:tutor_inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Estado de mis deudas')


class PlanConCajaSinFacturacionTests(BasePlanTestCase):
    """Caja activa pero facturación fuera: cobros sí, NCF no."""

    def setUp(self):
        cache.clear()
        self._crear_centro(modulo_caja=True)
        self.director = self._crear_usuario('dirmix', 'director')

    def test_caja_accesible_y_facturacion_bloqueada(self):
        self._login_con_centro(self.director)

        self.assertEqual(
            self.client.get(reverse('caja:caja_inicio')).status_code, 200
        )
        response = self.client.get(
            reverse('facturacion:lista_facturas'), follow=True
        )
        self.assertRedirects(
            response, reverse('administracion:dashboard_admin')
        )


class PlanCompletoTests(BasePlanTestCase):
    """Plan completo: ambos módulos responden normalmente."""

    def setUp(self):
        cache.clear()
        self._crear_centro(modulo_caja=True, permitir_facturacion=True)
        self.director = self._crear_usuario('dirfull', 'director')

    def test_ambos_modulos_accesibles(self):
        self._login_con_centro(self.director)

        self.assertEqual(
            self.client.get(reverse('caja:caja_inicio')).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse('facturacion:facturacion_inicio')
            ).status_code,
            200,
        )
        self.assertTrue(modulo_activo(self.centro.id, 'caja'))
        self.assertTrue(modulo_activo(self.centro.id, 'facturacion'))


class KardexDeudaTests(BasePlanTestCase):
    """Kardex: bloqueado con deuda (caja activa) y neutral sin el módulo."""

    def setUp(self):
        cache.clear()
        self._crear_centro(modulo_caja=True, modulo_certificados=True)
        self.director = self._crear_usuario('dirkdx', 'director')

        usuario_estudiante = self._crear_usuario('estkdx', 'estudiante')
        self.estudiante = Estudiante.objects.create(
            usuario=usuario_estudiante,
            centro=self.centro,
            matricula='20990001',
            primer_nombre='Ana',
            primer_apellido='Reyes',
            sexo='F',
            fecha_nacimiento='2011-01-15',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor',
            cedula_tutor='00100000001',
            telefono_tutor='809-555-0001',
            parentesco_tutor='Madre',
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )
        self.concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Inscripción',
            monto=5000,
            es_recurrente=False,
            activo=True,
        )
        AsignacionConcepto.objects.create(
            centro=self.centro,
            concepto=self.concepto,
            estudiante=self.estudiante,
            anio_escolar=self.anio,
        )

    def test_kardex_bloqueado_con_deuda(self):
        from caja.services import tiene_deuda_pendiente

        self.assertTrue(
            tiene_deuda_pendiente(self.centro, self.estudiante, self.anio)
        )
        self._login_con_centro(self.director)

        response = self.client.get(
            reverse('kardex_imprimir', args=[self.estudiante.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('constancias'))
        mensajes = ' '.join(
            str(m) for m in dj_messages.get_messages(response.wsgi_request)
        )
        self.assertIn('deuda pendiente', mensajes)

    def test_detalle_muestra_record_bloqueado(self):
        self._login_con_centro(self.director)

        contenido = self.client.get(
            reverse('estudiante_detail', args=[self.estudiante.pk])
        ).content.decode()

        self.assertIn('Record (deuda)', contenido)

    def test_al_pagar_se_desbloquea(self):
        from caja.models import Pago

        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=5000,
            fecha=date(2026, 6, 15),
        )
        cache.clear()
        self._login_con_centro(self.director)

        response = self.client.get(
            reverse('kardex_imprimir', args=[self.estudiante.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_sin_modulo_caja_no_se_bloquea(self):
        from caja.services import tiene_deuda_pendiente

        self.config.modulo_caja = False
        self.config.save()
        cache.clear()

        self.assertFalse(
            tiene_deuda_pendiente(self.centro, self.estudiante, self.anio)
        )
        self._login_con_centro(self.director)

        response = self.client.get(
            reverse('kardex_imprimir', args=[self.estudiante.pk])
        )

        self.assertEqual(response.status_code, 200)
