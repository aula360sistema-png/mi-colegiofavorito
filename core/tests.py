from django.core.cache import cache
from django.core import mail
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.models import CentroEducativo, ConfiguracionCentro
from core.services import centros_listado
from usuarios.models import Usuario


class CacheCentrosListadoTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Alfa',
            codigo_minerd='MIN-C1'
        )

    def test_segunda_llamada_sin_consultas(self):
        primera = centros_listado()
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = centros_listado()
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nuevo_centro_invalida_listado(self):
        antes = centros_listado()
        self.assertEqual(len(antes), 1)

        CentroEducativo.objects.create(
            nombre='Colegio Beta',
            codigo_minerd='MIN-C2'
        )

        despues = centros_listado()
        self.assertEqual(len(despues), 2)

    def test_borrar_centro_invalida_listado(self):
        antes = centros_listado()
        self.assertEqual(len(antes), 1)

        self.centro.delete()

        despues = centros_listado()
        self.assertEqual(len(despues), 0)


class ConfiguracionCorreoCentralTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Prueba',
            codigo_minerd='MIN-CC1',
        )
        self.director = Usuario.objects.create_user(
            username='director_cfg',
            email='director@prueba.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

    def _login(self):
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_formulario_incluye_campos_de_correo(self):
        self._login()
        ConfiguracionCentro.objects.create(centro=self.centro)
        response = self.client.get(reverse('core:configuracion_centro'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email_servidor')
        self.assertContains(response, 'whatsapp_url')

    def test_guardar_configuracion_correo(self):
        self._login()
        config = ConfiguracionCentro.objects.create(centro=self.centro)

        response = self.client.post(
            reverse('core:configuracion_centro'),
            {
                'usa_calificacion_numerica': 'on',
                'nota_minima_aprobacion': '70.00',
                'usa_competencias': 'on',
                'permite_completivo': 'on',
                'tipo_pago_nomina': 'mensual',
                'modulo_asistencia': 'on',
                'modulo_caja': 'on',
                'modulo_mensajeria': 'on',
                'modulo_reportes': 'on',
                'precio_certificado': '0.00',
                'email_servidor': 'smtp.gmail.com',
                'email_puerto': '587',
                'email_usuario': 'correo@prueba.com',
                'email_clave': 'clave-secreta',
                'email_tls': 'on',
                'email_remitente': 'notificaciones@prueba.com',
                'whatsapp_url': 'https://gw.prueba.com/wa',
                'whatsapp_token': 'token-123',
            },
        )
        self.assertEqual(response.status_code, 302)

        config.refresh_from_db()
        self.assertEqual(config.email_servidor, 'smtp.gmail.com')
        self.assertEqual(config.email_usuario, 'correo@prueba.com')
        self.assertEqual(config.email_clave, 'clave-secreta')
        self.assertEqual(config.whatsapp_url, 'https://gw.prueba.com/wa')
        self.assertTrue(config.email_tls)

    def test_correo_de_prueba_enviado(self):
        self._login()
        response = self.client.post(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['director@prueba.com'])
        self.assertIn('prueba', mail.outbox[0].body)

    def test_correo_de_prueba_sin_email_de_usuario(self):
        self.director.email = ''
        self.director.save()
        self._login()

        response = self.client.post(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_de_prueba_solo_por_post(self):
        self._login()
        response = self.client.get(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
