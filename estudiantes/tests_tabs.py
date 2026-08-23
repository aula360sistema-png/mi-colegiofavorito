from django.test import TestCase

from core.models import CentroEducativo
from core.tests import _crear_usuario
from estudiantes.models import Estudiante


class EstudianteDetailTabsTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Tabs', codigo_minerd='MIN-TAB1'
        )
        self.director = _crear_usuario('dirtabs', rol='director')
        self.estudiante = Estudiante.objects.create(
            usuario=_crear_usuario('esttabs', rol='estudiante'),
            centro=self.centro,
            matricula='20990001',
            primer_nombre='Tab',
            primer_apellido='Tester',
            sexo='M',
            fecha_nacimiento='2010-05-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor',
            cedula_tutor='00100000001',
            telefono_tutor='809-555-0001',
            parentesco_tutor='Madre',
        )

    def _login(self):
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_detalle_renderiza_tabs(self):
        self._login()
        respuesta = self.client.get(
            f'/estudiantes/{self.estudiante.id}/', follow=True
        )
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertIn('data-target="kardex"', contenido)
        self.assertIn('data-target="matriculas"', contenido)
        self.assertIn('id="tab-kardex"', contenido)
        self.assertIn('id="tab-matriculas"', contenido)

    def test_kardex_imprimir_funciona(self):
        self._login()
        respuesta = self.client.get(
            f'/estudiantes/{self.estudiante.id}/kardex/imprimir/'
        )
        self.assertEqual(respuesta.status_code, 200)
