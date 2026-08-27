from datetime import date

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from academico.models import Grado, Nivel
from administracion.models import Acta
from administracion.views import actas_del_centro
from core.models import AnioEscolar, CentroEducativo
from estudiantes.models import Estudiante
from usuarios.models import Usuario


def _crear_estudiante(centro, usuario, matricula, nombre, apellido):
    return Estudiante.objects.create(
        usuario=usuario,
        centro=centro,
        matricula=matricula,
        primer_nombre=nombre,
        primer_apellido=apellido,
        sexo='M',
        fecha_nacimiento=date(2010, 1, 1),
        lugar_nacimiento='Santo Domingo',
        nacionalidad='Dominicana',
        direccion='Calle 1',
        nombre_tutor='Maria Perez',
        cedula_tutor='00000000000',
        telefono_tutor='8090000000',
        parentesco_tutor='Madre',
    )


class CacheActasDelCentroTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria'
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='1ro',
            orden=1
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

        self.estudiante = _crear_estudiante(
            self.centro,
            self.usuario,
            'MAT-0001',
            'Juan',
            'Perez',
        )

        self.acta = Acta.objects.create(
            centro=self.centro,
            anio_escolar=self.anio,
            estudiante=self.estudiante,
            grado=self.grado,
            seccion='A',
            datos={'estado_final': 'aprobado'},
            generado_por=self.usuario,
        )

    def test_segunda_llamada_sin_consultas(self):
        primera = actas_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = actas_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0].id, self.acta.id)

    def test_nueva_acta_invalida_lista(self):
        primera = actas_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        otro_usuario = Usuario.objects.create_user(
            username='estudiante2',
            email='est2@test.com',
            password='clave123',
        )
        otro_estudiante = _crear_estudiante(
            self.centro,
            otro_usuario,
            'MAT-0002',
            'Ana',
            'Lopez',
        )
        Acta.objects.create(
            centro=self.centro,
            anio_escolar=self.anio,
            estudiante=otro_estudiante,
            grado=self.grado,
            seccion='B',
            datos={'estado_final': 'reprobado'},
            generado_por=self.usuario,
        )

        despues = actas_del_centro(self.centro)
        self.assertEqual(len(despues), 2)


# ---------------------------------------------------------------------------
# Tests del Dashboard de Promociones
# ---------------------------------------------------------------------------

from django.urls import reverse

from academico.models import Seccion, Periodo, PeriodoAnio
from administracion.views import _estado_cierre_anio, promociones_dashboard, promociones_recuperacion
from core.models import ConfiguracionCentro, CierreAnio
from estudiantes.models import Inscripcion


class PromocionesDashboardTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Promociones',
            codigo_minerd='MIN-PROM1',
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria',
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='3ro',
            orden=3,
        )
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.usuario = Usuario.objects.create_user(
            username='dir_promo',
            email='dir@promo.com',
            password='clave123',
        )
        self.usuario.rol = 'director'
        self.usuario.save()

        ConfiguracionCentro.objects.create(
            centro=self.centro,
            nota_minima_aprobacion=70,
        )

    def _login(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_estado_cierre_sin_anio(self):
        self.anio.delete()
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNone(resultado)

    def test_estado_cierre_anio_activo_sin_datos(self):
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['periodos_total'], 0)
        self.assertFalse(resultado['periodos_ok'])
        self.assertEqual(resultado['boletines_total'], 0)
        self.assertTrue(resultado['boletines_ok'])
        self.assertEqual(resultado['en_recuperacion'], 0)
        self.assertTrue(resultado['completivo_ok'])
        self.assertFalse(resultado['anio_cerrado'])
        self.assertIsNone(resultado['cierre'])
        self.assertFalse(resultado['promocion_ejecutada'])

    def test_estado_cierre_periodos_cerrados(self):
        p1 = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1, es_completivo=False
        )
        PeriodoAnio.objects.create(
            periodo=p1, anio_escolar=self.anio, activo=True, cerrado=True
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['periodos_total'], 1)
        self.assertEqual(resultado['periodos_cerrados'], 1)
        self.assertTrue(resultado['periodos_ok'])

    def test_estado_cierre_periodos_abiertos(self):
        p1 = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1, es_completivo=False
        )
        PeriodoAnio.objects.create(
            periodo=p1, anio_escolar=self.anio, activo=True, cerrado=False
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['periodos_total'], 1)
        self.assertEqual(resultado['periodos_cerrados'], 0)
        self.assertFalse(resultado['periodos_ok'])

    def test_dashboard_renderiza(self):
        self._login()
        response = self.client.get(reverse('administracion:promociones_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cierre de Año Escolar y Promociones')

    def test_dashboard_sin_anio_muestra_mensaje(self):
        self._login()
        self.anio.delete()
        response = self.client.get(reverse('administracion:promociones_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay año escolar activo')

    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse('administracion:promociones_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_requiere_rol(self):
        otro = Usuario.objects.create_user(
            username='docente_promo', email='d@p.com', password='clave123'
        )
        otro.rol = 'docente'
        otro.save()
        self.client.force_login(otro)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('administracion:promociones_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_estado_cierre_con_cierre_anio(self):
        cierre = CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.usuario,
            totales={'inscritos': 0, 'aprobados': 0},
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertIsNotNone(resultado['cierre'])
        self.assertTrue(resultado['promocion_ejecutada'])

    def test_estado_cierre_fallback_año_cerrado(self):
        CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.usuario,
            totales={'inscritos': 5, 'aprobados': 4},
        )
        self.anio.activo = False
        self.anio.cerrado = True
        self.anio.save()
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['anio'], self.anio)
        self.assertTrue(resultado['anio_cerrado'])
        self.assertTrue(resultado['promocion_ejecutada'])

    def test_estado_cierre_completivo_existe(self):
        pc = Periodo.objects.create(
            centro=self.centro, nombre='Completivo', orden=10, es_completivo=True
        )
        PeriodoAnio.objects.create(
            periodo=pc, anio_escolar=self.anio, activo=True, cerrado=False
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertTrue(resultado['completivo_existe'])
        self.assertTrue(resultado['completivo_abierto'])

    def test_estado_cierre_estudiantes_en_recuperacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R1', 'Pedro', 'Gomez'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='recuperacion',
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['en_recuperacion'], 1)
        self.assertFalse(resultado['completivo_ok'])

    def test_sin_calificacion_bloquea_false_when_none(self):
        resultado = _estado_cierre_anio(self.centro)
        self.assertFalse(resultado['sin_calificacion_bloquea'])

    def test_sin_calificacion_bloquea_true_when_present(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-SC1', 'Ana', 'Lopez'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='sin_calificacion',
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertTrue(resultado['sin_calificacion_bloquea'])
        self.assertEqual(resultado['sin_calificacion'], 1)

    def test_dashboard_bloquea_paso4_con_sin_calificacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-SC2', 'Carlos', 'Ruiz'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='sin_calificacion',
        )
        self._login()
        response = self.client.get(reverse('administracion:promociones_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bloqueado')
        self.assertContains(response, 'sin calificaciones')
        self.assertContains(response, 'Resuelva antes de cerrar')


# ---------------------------------------------------------------------------
# Tests de la vista de Recuperación
# ---------------------------------------------------------------------------

class PromocionesRecuperacionTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Recuperacion',
            codigo_minerd='MIN-REC1',
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria',
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='2do',
            orden=2,
        )
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='B')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.usuario = Usuario.objects.create_user(
            username='dir_rec',
            email='dir@rec.com',
            password='clave123',
        )
        self.usuario.rol = 'director'
        self.usuario.save()

        ConfiguracionCentro.objects.create(
            centro=self.centro,
            nota_minima_aprobacion=70,
        )

    def _login(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_recuperacion_vacia(self):
        self._login()
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay estudiantes pendientes')

    def test_recuperacion_redirect_sin_anio(self):
        self._login()
        self.anio.delete()
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 302)

    def test_recuperacion_requiere_login(self):
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 302)

    def test_recuperacion_requiere_rol(self):
        otro = Usuario.objects.create_user(
            username='docente_rec', email='d@r.com', password='clave123'
        )
        otro.rol = 'docente'
        otro.save()
        self.client.force_login(otro)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 403)

    def test_recuperacion_con_estudiante_reprobado(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R2', 'Luis', 'Torres'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='recuperacion',
        )
        self._login()
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estudiantes en Recuperación')

    def test_recuperacion_excluye_no_recuperacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R3', 'Maria', 'Diaz'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='aprobado',
        )
        self._login()
        response = self.client.get(reverse('administracion:promociones_recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay estudiantes pendientes')
