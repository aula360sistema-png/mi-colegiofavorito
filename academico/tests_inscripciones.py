"""Pruebas del cambio de sección de inscripciones (post-promoción)
y del selector de año en la vista de estudiantes por grado.
"""

from django.urls import reverse

from academico.models import Seccion
from academico.services.inscripciones import (
    CambiarSeccionError,
    cambiar_seccion,
)
from auditoria.models import Bitacora
from core.models import AnioEscolar

from .tests_notas import BaseNotasTestCase


class CambiarSeccionServicioTests(BaseNotasTestCase):

    def setUp(self):
        super().setUp()
        self.seccion_b = Seccion.objects.create(
            centro=self.centro, nombre='B'
        )
        self.grados['1ro de Primaria'].secciones.add(self.seccion_b)
        self.inscripcion = self._inscribir(
            self._estudiante('97000001'), '1ro de Primaria'
        )

    def test_mueve_y_audita(self):
        anterior, nueva = cambiar_seccion(
            self.inscripcion, self.seccion_b, self.director
        )
        self.inscripcion.refresh_from_db()

        self.assertEqual(anterior.nombre, 'A')
        self.assertEqual(nueva, self.seccion_b)
        self.assertEqual(self.inscripcion.seccion_id, self.seccion_b.id)

        bitacora = Bitacora.objects.filter(
            accion='EDITAR',
            modelo='Inscripcion',
            objeto_id=self.inscripcion.id,
        )
        self.assertTrue(bitacora.exists())
        self.assertEqual(
            bitacora.latest('id').datos_nuevos['seccion'], 'B'
        )

    def test_rechaza_seccion_de_otro_centro(self):
        otro = Seccion.objects.create(
            centro_id=self._otro_centro(), nombre='Z'
        )
        with self.assertRaises(CambiarSeccionError):
            cambiar_seccion(self.inscripcion, otro, self.director)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.seccion.nombre, 'A')

    def _otro_centro(self):
        from core.models import CentroEducativo

        centro = CentroEducativo.objects.create(
            nombre='Otro Colegio',
            codigo_minerd='MIN-9999',
        )
        return centro.id

    def test_rechaza_seccion_no_vinculada_al_grado(self):
        suelta = Seccion.objects.create(centro=self.centro, nombre='C')
        with self.assertRaises(CambiarSeccionError):
            cambiar_seccion(self.inscripcion, suelta, self.director)

    def test_rechaza_misma_seccion(self):
        with self.assertRaises(CambiarSeccionError):
            cambiar_seccion(
                self.inscripcion, self.inscripcion.seccion, self.director
            )


class CambiarSeccionVistaTests(BaseNotasTestCase):

    def setUp(self):
        super().setUp()
        self.seccion_b = Seccion.objects.create(
            centro=self.centro, nombre='B'
        )
        self.grados['1ro de Primaria'].secciones.add(self.seccion_b)
        self.inscripcion = self._inscribir(
            self._estudiante('98000001'), '1ro de Primaria'
        )
        self.url = reverse(
            'inscripcion_cambiar_seccion', args=[self.inscripcion.id]
        )

    def test_ajax_mueve_estudiante(self):
        self._login(self.secretaria)
        respuesta = self.client.post(
            self.url,
            {'seccion': self.seccion_b.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['success'])
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.seccion_id, self.seccion_b.id)

    def test_ajax_error_devuelve_400(self):
        suelta = Seccion.objects.create(centro=self.centro, nombre='C')
        self._login(self.director)
        respuesta = self.client.post(
            self.url,
            {'seccion': suelta.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['success'])
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.seccion.nombre, 'A')

    def test_sin_ajax_redirige_con_mensaje(self):
        self._login(self.director)
        respuesta = self.client.post(
            self.url, {'seccion': self.seccion_b.id}, follow=True
        )

        mensajes = [str(m) for m in respuesta.context['messages']]
        self.assertTrue(any('movido a la sección B' in m for m in mensajes))
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.seccion_id, self.seccion_b.id)

    def test_get_no_permitido(self):
        self._login(self.director)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 405)


class GradoEstudiantesAnioParamTests(BaseNotasTestCase):

    def test_parametro_anio_muestra_otro_anio(self):
        grado = self.grados['1ro de Primaria']
        futuro = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2025-2026',
            fecha_inicio='2025-08-01',
            fecha_fin='2026-07-31',
            activo=False,
        )
        estudiante = self._estudiante('99000009')
        from estudiantes.models import Inscripcion

        Inscripcion.objects.create(
            estudiante=estudiante,
            centro=self.centro,
            anio_escolar=futuro,
            grado=grado,
            seccion=self.seccion_a,
        )

        self._login(self.director)
        url = reverse('grado_estudiantes', args=[grado.pk])
        respuesta = self.client.get(f'{url}?anio={futuro.pk}')

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['anio_escolar'], futuro)
        self.assertContains(respuesta, estudiante.nombre_completo())
