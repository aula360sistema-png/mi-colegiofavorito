"""Pruebas del cierre de año escolar, bitácora, reapertura,
promoción masiva, respaldo y acta de sección.
"""

from datetime import date

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academico.models import Seccion
from academico.services.estructura_minerd import crear_estructura_minerd
from core.models import (
    AnioEscolar,
    CentroEducativo,
    CierreAnio,
    ConfiguracionCentro,
)
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario


class BaseCierreTestCase(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Cierre',
            codigo_minerd='MIN-7777',
        )
        ConfiguracionCentro.objects.create(centro=self.centro)

        self.director = self._usuario('dircierre', 'director')
        self.secretaria = self._usuario('secre', 'secretaria')

        estructura = crear_estructura_minerd(
            self.centro, ('primaria',)
        )
        self.grados = {
            g.nombre: g for g in estructura['grados']
        }
        self.seccion_a = Seccion.objects.create(
            centro=self.centro, nombre='A'
        )
        for grado in self.grados.values():
            self.seccion_a.grados.add(grado)

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2024-2025',
            fecha_inicio=date(2024, 8, 1),
            fecha_fin=date(2025, 7, 31),
            activo=True,
        )

    def _usuario(self, username, rol):
        usuario = Usuario.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='clave123',
        )
        usuario.rol = rol
        usuario.save()
        return usuario

    def _login(self, usuario):
        self.client.login(
            username=usuario.username, password='clave123'
        )
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _estudiante(self, matricula, nombre='Est'):
        usuario = self._usuario(
            f'u{matricula[-5:]}', 'estudiante'
        )
        return Estudiante.objects.create(
            usuario=usuario,
            centro=self.centro,
            matricula=matricula,
            primer_nombre=nombre,
            primer_apellido='Prueba',
            sexo='M',
            fecha_nacimiento='2012-05-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor Prueba',
            cedula_tutor='00100000001',
            telefono_tutor='809-555-0000',
            parentesco_tutor='Madre',
        )

    def _inscribir(self, estudiante, grado_nombre, estado):
        return Inscripcion.objects.create(
            estudiante=estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grados[grado_nombre],
            seccion=self.seccion_a,
            estado_final=estado,
        )


class CierreAnioTests(BaseCierreTestCase):

    def test_cierre_registra_bitacora_completa(self):
        self._inscribir(self._estudiante('21000001'), '1ro de Primaria', 'aprobado')
        self._inscribir(self._estudiante('21000002'), '1ro de Primaria', 'reprobado')

        self._login(self.director)
        response = self.client.get(
            reverse('cerrar_anio_escolar', args=[self.anio.pk]), follow=True
        )

        self.anio.refresh_from_db()
        self.assertTrue(self.anio.cerrado)
        self.assertFalse(self.anio.activo)

        cierre = CierreAnio.objects.get(anio_escolar=self.anio)
        self.assertEqual(cierre.usuario, self.director)
        self.assertEqual(cierre.totales['inscritos'], 2)
        self.assertEqual(cierre.totales['aprobado'], 1)
        self.assertEqual(cierre.totales['reprobado'], 1)
        # Sin módulo de caja: sin deudores (modo neutral).
        self.assertEqual(cierre.deudores, [])
        mensajes = [str(m) for m in dj_msgs(response)]
        self.assertFalse(any('Deuda' in m for m in mensajes))

    def test_cierre_bloqueado_por_pendientes(self):
        self._inscribir(self._estudiante('21000003'), '2do de Primaria', 'pendiente')

        self._login(self.director)
        self.client.get(
            reverse('cerrar_anio_escolar', args=[self.anio.pk]), follow=True
        )

        self.anio.refresh_from_db()
        self.assertFalse(self.anio.cerrado)
        self.assertFalse(CierreAnio.objects.exists())

    def test_reabrir_exige_rol_director_o_admin(self):
        self.anio.cerrar()
        CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.director,
        )

        self._login(self.secretaria)
        response = self.client.post(
            reverse('reabrir_anio_escolar', args=[self.anio.pk]),
            {'motivo': 'corrección necesaria de estados finales'},
            follow=True,
        )
        self.assertIn(response.status_code, (302, 403))

        self.anio.refresh_from_db()
        self.assertTrue(self.anio.cerrado)

    def test_reabrir_rechaza_motivo_corto(self):
        self.anio.cerrar()

        self._login(self.director)
        self.client.post(
            reverse('reabrir_anio_escolar', args=[self.anio.pk]),
            {'motivo': 'corto'},
            follow=True,
        )

        self.anio.refresh_from_db()
        self.assertTrue(self.anio.cerrado)

    def test_reabrir_con_motivo_queda_auditado(self):
        self.anio.cerrar()
        cierre = CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.director,
        )

        self._login(self.director)
        self.client.post(
            reverse('reabrir_anio_escolar', args=[self.anio.pk]),
            {'motivo': 'Se registró mal el estado final de un estudiante'},
            follow=True,
        )

        self.anio.refresh_from_db()
        cierre.refresh_from_db()
        self.assertFalse(self.anio.cerrado)
        self.assertTrue(cierre.reabierto)
        self.assertEqual(
            cierre.motivo_reapertura,
            'Se registró mal el estado final de un estudiante',
        )
        self.assertIsNotNone(cierre.fecha_reapertura)


def dj_msgs(response):
    from django.contrib import messages as dj_messages
    return list(dj_messages.get_messages(response.wsgi_request))


class PromocionMasivaTests(BaseCierreTestCase):

    def setUp(self):
        super().setUp()
        self.nuevo = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2025-2026',
            fecha_inicio=date(2025, 8, 1),
            fecha_fin=date(2026, 7, 31),
            activo=False,
        )

    def test_ejecutar_promueve_repite_y_omite(self):
        aprobado = self._estudiante('22000001')
        reprobado = self._estudiante('22000002')
        retirado = self._estudiante('22000003')

        self._inscribir(aprobado, '1ro de Primaria', 'aprobado')
        self._inscribir(reprobado, '1ro de Primaria', 'reprobado')
        self._inscribir(retirado, '1ro de Primaria', 'retirado')

        self.anio.cerrar()
        self._login(self.director)

        response = self.client.post(
            reverse('promocion_ejecutar', args=[self.anio.pk]),
            {
                'anio_destino': self.nuevo.pk,
                f'seccion_{self.grados["2do de Primaria"].id}': self.seccion_a.id,
                f'seccion_{self.grados["1ro de Primaria"].id}': self.seccion_a.id,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            Inscripcion.objects.filter(
                estudiante=aprobado,
                anio_escolar=self.nuevo,
                grado=self.grados['2do de Primaria'],
            ).exists()
        )
        self.assertTrue(
            Inscripcion.objects.filter(
                estudiante=reprobado,
                anio_escolar=self.nuevo,
                grado=self.grados['1ro de Primaria'],
            ).exists()
        )
        self.assertFalse(
            Inscripcion.objects.filter(estudiante=retirado).count() > 1
        )

        # Idempotente: segunda pasada no duplica.
        self.client.post(
            reverse('promocion_ejecutar', args=[self.anio.pk]),
            {
                'anio_destino': self.nuevo.pk,
                f'seccion_{self.grados["2do de Primaria"].id}': self.seccion_a.id,
                f'seccion_{self.grados["1ro de Primaria"].id}': self.seccion_a.id,
            },
        )
        self.assertEqual(
            Inscripcion.objects.filter(anio_escolar=self.nuevo).count(),
            2,
        )

    def test_condicional_se_promueve_y_no_se_omite(self):
        condicional = self._estudiante('22000006')
        self._inscribir(
            condicional, '1ro de Primaria', 'promocion_condicional'
        )

        self.anio.cerrar()
        self._login(self.director)

        response = self.client.post(
            reverse('promocion_ejecutar', args=[self.anio.pk]),
            {
                'anio_destino': self.nuevo.pk,
                f'seccion_{self.grados["2do de Primaria"].id}': self.seccion_a.id,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # El condicional no debe quedar fuera del plan: se promueve.
        self.assertTrue(
            Inscripcion.objects.filter(
                estudiante=condicional,
                anio_escolar=self.nuevo,
                grado=self.grados['2do de Primaria'],
            ).exists()
        )

    def test_preview_muestra_plan_y_destino(self):
        self._inscribir(self._estudiante('22000004'), '3ro de Primaria', 'aprobado')
        self.anio.cerrar()

        self._login(self.director)
        response = self.client.get(
            reverse('promocion_preview', args=[self.anio.pk])
        )

        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode('utf-8')
        self.assertIn('2025-2026', contenido)
        self.assertIn('Promoción masiva', contenido)

    def test_ultimo_grado_no_se_inscribe(self):
        egresado = self._estudiante('22000005')
        self._inscribir(egresado, '6to de Primaria', 'aprobado')
        self.anio.cerrar()
        self._login(self.director)

        self.client.post(
            reverse('promocion_ejecutar', args=[self.anio.pk]),
            {
                'anio_destino': self.nuevo.pk,
            },
        )

        self.assertFalse(
            Inscripcion.objects.filter(
                estudiante=egresado, anio_escolar=self.nuevo
            ).exists()
        )


class RespaldoYActaTests(BaseCierreTestCase):

    def test_respaldo_descarga_json_con_datos(self):
        inscripcion = self._inscribir(
            self._estudiante('23000001'), '4to de Primaria', 'aprobado'
        )
        self._login(self.director)

        response = self.client.get(
            reverse('respaldo_anio', args=[self.anio.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])

        datos = response.json()
        self.assertEqual(datos['anio_escolar']['nombre'], '2024-2025')
        self.assertEqual(len(datos['inscripciones']), 1)
        self.assertEqual(
            datos['inscripciones'][0]['matricula'],
            '23000001',
        )

    def test_acta_seccion_renderiza_estudiantes(self):
        self._inscribir(
            self._estudiante('24000001'), '5to de Primaria', 'aprobado'
        )

        self._login(self.director)
        response = self.client.get(
            reverse('acta_seccion'),
            {
                'anio': self.anio.pk,
                'grado': self.grados['5to de Primaria'].pk,
                'seccion': self.seccion_a.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode('utf-8')
        self.assertIn('Acta final de sección', contenido)
        self.assertIn('24000001', contenido)
