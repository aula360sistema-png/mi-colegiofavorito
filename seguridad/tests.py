from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import AnioEscolar, CentroEducativo
from estudiantes.models import Estudiante, Inscripcion
from entrenamiento.models import TramoEdad

from .models import ConsentimientoInformado, RegistroAccesoDato, RegistroRetencion
from .utils import (
    anonimizar_cedula,
    anonimizar_email,
    anonimizar_nombre,
    anonimizar_telefono,
    cifrar_campo,
    descifrar_campo,
)

Usuario = get_user_model()


class TestUtils(TestCase):

    def setUp(self):
        from django.conf import settings
        settings.ENCRYPTION_KEY = '4QS91i9O3YRwP6CULSXtenLZ9-3ea9QOyS-ljIoisC8='

    def test_cifrar_descifrar(self):
        original = 'texto sensible 123'
        cifrado = cifrar_campo(original)
        self.assertNotEqual(cifrado, original)
        descifrado = descifrar_campo(cifrado)
        self.assertEqual(descifrado, original)

    def test_cifrar_vacio(self):
        self.assertEqual(cifrar_campo(''), '')
        self.assertIsNone(cifrar_campo(None))

    def test_descifrar_invalido(self):
        result = descifrar_campo('not-encrypted-text')
        self.assertEqual(result, 'not-encrypted-text')

    def test_anonimizar_nombre(self):
        self.assertEqual(anonimizar_nombre('Juan'), 'J***')
        self.assertEqual(anonimizar_nombre('A'), '*')
        self.assertEqual(anonimizar_nombre(''), '***')

    def test_anonimizar_cedula(self):
        result = anonimizar_cedula('402-1234567-8')
        self.assertTrue(result.startswith('40'))
        self.assertNotIn('1234567', result)

    def test_anonimizar_telefono(self):
        result = anonimizar_telefono('8091234567')
        self.assertTrue(result.endswith('4567'))
        self.assertEqual(len(result), 10)

    def test_anonimizar_email(self):
        result = anonimizar_email('juan@test.com')
        self.assertIn('@test.com', result)
        self.assertNotIn('juan', result)


class BaseSeguridadTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Seguridad', direccion='Calle 1',
            telefono='8090000000', email='sec@test.com',
        )
        self.anio = AnioEscolar.objects.create(
            centro=self.centro, nombre='2026-2027',
            fecha_inicio=date(2026, 8, 20), fecha_fin=date(2027, 6, 30),
            activo=True,
        )
        self.director = Usuario.objects.create_user(
            username='dir_sec', email='dir@test.com', password='clave123A!',
        )
        self.director.rol = 'director'
        self.director.save()
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        self.estudiante_user = Usuario.objects.create_user(
            username='est_sec', email='est@test.com', password='clave123A!',
        )
        self.estudiante_user.rol = 'estudiante'
        self.estudiante_user.save()
        self.estudiante = Estudiante.objects.create(
            usuario=self.estudiante_user, centro=self.centro,
            matricula='MAT-SEC-001', primer_nombre='Maria', primer_apellido='Lopez',
            sexo='F', fecha_nacimiento=date(2014, 5, 10),
            lugar_nacimiento='Santiago', nacionalidad='Dominicana',
            direccion='Calle 2', nombre_tutor='Pedro Lopez',
            cedula_tutor='40211122233', telefono_tutor='8091112233',
            parentesco_tutor='Padre',
        )
        self.tramo = TramoEdad.objects.create(
            nombre='Destrezas I', edad_min=7, edad_max=9, orden=1,
        )


class ConsentimientoTests(BaseSeguridadTestCase):

    def test_consentimiento_list_renders(self):
        response = self.client.get(reverse('seguridad:consentimiento_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consentimientos Informados')

    def test_consentimiento_create(self):
        response = self.client.post(reverse('seguridad:consentimiento_create'), {
            'estudiante': self.estudiante.pk,
            'tutor_nombre': 'Pedro Lopez',
            'tutor_cedula': '40211122233',
            'tutor_parentesco': 'Padre',
            'acepta_datos_personales': True,
            'acepta_datos_academicos': True,
            'acepta_datos_clinicos': False,
            'acepta_comunicaciones': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ConsentimientoInformado.objects.filter(
                estudiante=self.estudiante,
                tutor_nombre='Pedro Lopez',
            ).exists()
        )

    def test_consentimiento_detail_renders(self):
        consent = ConsentimientoInformado.objects.create(
            estudiante=self.estudiante, centro=self.centro, anio_escolar=self.anio,
            tutor_nombre='Pedro Lopez', tutor_cedula='40211122233',
            tutor_parentesco='Padre', acepta_datos_personales=True,
        )
        response = self.client.get(
            reverse('seguridad:consentimiento_detail', args=[consent.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedro Lopez')

    def test_consentimiento_revocar(self):
        consent = ConsentimientoInformado.objects.create(
            estudiante=self.estudiante, centro=self.centro, anio_escolar=self.anio,
            tutor_nombre='Pedro Lopez', tutor_cedula='40211122233',
            tutor_parentesco='Padre', acepta_datos_personales=True,
        )
        response = self.client.post(
            reverse('seguridad:consentimiento_revocar', args=[consent.pk]),
            {'motivo': 'Solicitud del tutor'},
        )
        self.assertEqual(response.status_code, 302)
        consent.refresh_from_db()
        self.assertFalse(consent.activo)
        self.assertIsNotNone(consent.fecha_revocacion)

    def test_tiene_consentimiento(self):
        consent = ConsentimientoInformado.objects.create(
            estudiante=self.estudiante, centro=self.centro, anio_escolar=self.anio,
            tutor_nombre='Pedro Lopez', tutor_cedula='40211122233',
            tutor_parentesco='Padre', acepta_datos_personales=True,
            acepta_datos_academicos=False,
        )
        self.assertTrue(consent.tiene_consentimiento('datos_personales'))
        self.assertFalse(consent.tiene_consentimiento('datos_academicos'))
        consent.revocar('Test')
        self.assertFalse(consent.tiene_consentimiento('datos_personales'))


class RegistroAccesoTests(BaseSeguridadTestCase):

    def test_registros_acceso_renders(self):
        RegistroAccesoDato.objects.create(
            usuario=self.director, tipo_dato='datos_personales',
            accion='lectura', ip='127.0.0.1',
        )
        response = self.client.get(reverse('seguridad:registros_acceso'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registro de Acceso a Datos')

    def test_consentimiento_create_logs_acceso(self):
        self.client.post(reverse('seguridad:consentimiento_create'), {
            'estudiante': self.estudiante.pk,
            'tutor_nombre': 'Pedro Lopez',
            'tutor_cedula': '40211122233',
            'tutor_parentesco': 'Padre',
            'acepta_datos_personales': True,
        })
        self.assertTrue(
            RegistroAccesoDato.objects.filter(
                usuario=self.director,
                tipo_dato='datos_personales',
                accion='escritura',
            ).exists()
        )


class DashboardTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Dash', direccion='Calle 1',
            telefono='8090000000', email='dash@test.com',
        )
        self.admin_user = Usuario.objects.create_superuser(
            username='super_dash', email='super@test.com', password='clave123A!',
        )
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_dashboard_renders(self):
        response = self.client.get(reverse('seguridad:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seguridad de Datos')
        self.assertContains(response, 'Consentimientos Activos')


class RolesTests(BaseSeguridadTestCase):

    def test_estudiante_no_accede(self):
        est_user = Usuario.objects.create_user(
            username='est_noacceso', email='est2@test.com', password='clave123A!',
        )
        est_user.rol = 'estudiante'
        est_user.save()
        self.client.force_login(est_user)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('seguridad:dashboard'))
        self.assertIn(response.status_code, [302, 403])

    def test_no_autenticado_redirige_login(self):
        self.client.logout()
        response = self.client.get(reverse('seguridad:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
