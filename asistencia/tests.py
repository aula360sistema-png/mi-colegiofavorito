from datetime import date
from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from academico.models import (
    AreaCurricular,
    Asignatura,
    DocenteMateria,
    Grado,
    Nivel,
    Seccion,
)
from asistencia.models import AsistenciaEstudiante, DiaNoDocencia
from asistencia.services import (
    calcular_promedio_inscripcion,
    dias_lectivos,
    es_dia_lectivo,
    registros_del_dia,
    resumen_por_inscripciones,
)
from core.models import AnioEscolar, CentroEducativo
from docentes.models import Docente
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario


class AsistenciaServicesTestCase(TestCase):

    def setUp(self):
        cache.clear()
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 1, 16),
            activo=True
        )

        # Jueves 08/01/2026 marcado como día de no docencia
        DiaNoDocencia.objects.create(
            centro=self.centro,
            anio_escolar=self.anio,
            fecha=date(2026, 1, 8),
            motivo='Día de asueto'
        )

        usuario = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='clave123'
        )
        usuario.rol = 'estudiante'
        usuario.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario,
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
            parentesco_tutor='Madre'
        )

        nivel = Nivel.objects.create(centro=self.centro, nombre='Básica')
        grado = Grado.objects.create(nivel=nivel, nombre='1ro')
        seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        grado.secciones.add(seccion)

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=grado,
            seccion=seccion
        )
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(
            fecha=date(2026, 1, 5)
        )
        self.inscripcion.refresh_from_db()

    def registrar_asistencia(self, fecha, estado):
        AsistenciaEstudiante.objects.create(
            inscripcion=self.inscripcion,
            fecha=fecha,
            estado=estado
        )

    # --------------------------------------------------
    # es_dia_lectivo
    # --------------------------------------------------

    def test_dia_lectivo_dia_semana(self):
        self.assertTrue(es_dia_lectivo(self.anio, date(2026, 1, 5)))
        self.assertTrue(es_dia_lectivo(self.anio, date(2026, 1, 6)))

    def test_dia_no_lectivo_fin_de_semana(self):
        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 10)))
        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 11)))

    def test_dia_no_lectivo_por_no_docencia(self):
        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 8)))

    def test_dia_no_lectivo_fuera_del_rango(self):
        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 2)))
        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 17)))

    # --------------------------------------------------
    # dias_lectivos
    # --------------------------------------------------

    def test_dias_lectivos_excluye_fines_y_no_docencia(self):
        dias = dias_lectivos(self.anio, hasta=date(2026, 1, 9))

        self.assertEqual(dias, [
            date(2026, 1, 5),
            date(2026, 1, 6),
            date(2026, 1, 7),
            date(2026, 1, 9),
        ])

    def test_dias_lectivos_totales_del_periodo(self):
        dias = dias_lectivos(self.anio, hasta=date(2026, 1, 16))

        self.assertEqual(len(dias), 9)

    # --------------------------------------------------
    # calcular_promedio_inscripcion
    # --------------------------------------------------

    def test_promedio_antes_de_la_inscripcion(self):
        resultado = calcular_promedio_inscripcion(
            self.inscripcion,
            hasta=date(2026, 1, 1)
        )

        self.assertEqual(resultado['dias_lectivos'], 0)
        self.assertIsNone(resultado['porcentaje'])

    def test_promedio_parcial(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')
        self.registrar_asistencia(date(2026, 1, 6), 'presente')
        self.registrar_asistencia(date(2026, 1, 7), 'tardanza')
        self.registrar_asistencia(date(2026, 1, 9), 'ausente')

        resultado = calcular_promedio_inscripcion(
            self.inscripcion,
            hasta=date(2026, 1, 9)
        )

        self.assertEqual(resultado['dias_lectivos'], 4)
        self.assertEqual(resultado['asistencias'], 3)
        self.assertEqual(resultado['ausencias'], 1)
        self.assertEqual(resultado['porcentaje'], 75.0)

    def test_promedio_completo_con_estados_asistido(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')
        self.registrar_asistencia(date(2026, 1, 6), 'presente')
        self.registrar_asistencia(date(2026, 1, 7), 'tardanza')
        self.registrar_asistencia(date(2026, 1, 9), 'ausente')
        self.registrar_asistencia(date(2026, 1, 12), 'justificado')
        self.registrar_asistencia(date(2026, 1, 13), 'presente')

        resultado = calcular_promedio_inscripcion(
            self.inscripcion,
            hasta=date(2026, 1, 16)
        )

        self.assertEqual(resultado['dias_lectivos'], 9)
        self.assertEqual(resultado['asistencias'], 5)
        self.assertEqual(resultado['ausencias'], 1)
        self.assertEqual(resultado['porcentaje'], 55.56)

    def test_resumen_por_inscripciones(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')

        resumen = resumen_por_inscripciones(
            [self.inscripcion],
            hasta=date(2026, 1, 9)
        )

        self.assertEqual(len(resumen), 1)
        self.assertEqual(
            resumen[0]['inscripcion'],
            self.inscripcion
        )
        self.assertEqual(resumen[0]['porcentaje'], 25.0)


FECHA_RECORDATORIO = date(2026, 8, 10)  # lunes, día lectivo


class FakeDate(date):
    @classmethod
    def today(cls):
        return FECHA_RECORDATORIO


BASE_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


class RecordatorioAsistenciaTestCase(TestCase):

    def setUp(self):
        cache.clear()
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio R',
            codigo_minerd='MIN-9'
        )
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 12, 31),
            activo=True
        )

        self.nivel = Nivel.objects.create(centro=self.centro, nombre='Primaria')
        self.grado = Grado.objects.create(nivel=self.nivel, nombre='1ro')
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.grado.secciones.add(self.seccion)

        self.area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Ciencias'
        )
        self.asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=self.area,
            nombre='Matemática'
        )

        self.usuario_doc = Usuario.objects.create_user(
            username='doc1',
            email='doc1@test.com',
            password='clave123'
        )
        self.usuario_doc.rol = 'docente'
        self.usuario_doc.save()

        self.docente = Docente.objects.create(
            usuario=self.usuario_doc,
            centro=self.centro,
            primer_nombre='Ana',
            primer_apellido='Lopez',
            cedula='11111111111',
            sexo='F',
            fecha_nacimiento=date(1980, 1, 1),
            nacionalidad='Dominicana',
            direccion='Calle 1',
            telefono='8090000000',
            codigo_docente_minerd='D1',
            area_especialidad='Matemática',
            fecha_ingreso=date(2010, 1, 1),
            tipo_contrato='nombrado',
            tanda='matutina'
        )
        DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio
        )

        self.usuario_est = Usuario.objects.create_user(
            username='est1',
            email='est1@test.com',
            password='clave123'
        )
        self.usuario_est.rol = 'estudiante'
        self.usuario_est.save()

        self.estudiante = Estudiante.objects.create(
            usuario=self.usuario_est,
            centro=self.centro,
            matricula='M1',
            primer_nombre='Juan',
            primer_apellido='Perez',
            sexo='M',
            fecha_nacimiento=date(2010, 1, 1),
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Maria Perez',
            cedula_tutor='22222222222',
            telefono_tutor='8090000000',
            parentesco_tutor='Madre'
        )
        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion
        )
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(fecha=FECHA_RECORDATORIO)
        self.inscripcion.refresh_from_db()

    def cliente_docente(self):
        c = Client()
        c.force_login(self.usuario_doc)
        return c

    @mock.patch('asistencia.views.date', FakeDate)
    def test_endpoint_pendiente_y_resuelto(self):
        with override_settings(MIDDLEWARE=BASE_MIDDLEWARE, ALLOWED_HOSTS=['testserver']):
            c = self.cliente_docente()

            r = c.get(reverse('asistencia:estado_asistencia'))
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), {'pendiente': True})

            AsistenciaEstudiante.objects.create(
                inscripcion=self.inscripcion,
                fecha=FECHA_RECORDATORIO,
                estado='presente',
                registrada_por=self.usuario_doc
            )

            r = c.get(reverse('asistencia:estado_asistencia'))
            self.assertEqual(r.json(), {'pendiente': False})

    @mock.patch('asistencia.views.date', FakeDate)
    def test_fecha_bloqueada_al_dia_actual(self):
        with override_settings(MIDDLEWARE=BASE_MIDDLEWARE, ALLOWED_HOSTS=['testserver']):
            c = self.cliente_docente()

            r = c.get(reverse('asistencia:tomar_asistencia'), {
                'grado': self.grado.id,
                'seccion': self.seccion.id,
            })
            self.assertEqual(r.status_code, 200)
            html = r.content.decode('utf-8')

            hoy_real = date.today().isoformat()
            self.assertIn(f'min="{hoy_real}"', html)
            self.assertIn(f'max="{hoy_real}"', html)
            self.assertIn(f'value="{FECHA_RECORDATORIO.isoformat()}"', html)
            self.assertIn('readonly', html)

    @mock.patch('asistencia.views.date', FakeDate)
    def test_boton_deshabilitado_para_docente_despues_de_guardar(self):
        with override_settings(MIDDLEWARE=BASE_MIDDLEWARE, ALLOWED_HOSTS=['testserver']):
            c = self.cliente_docente()
            url = reverse('asistencia:tomar_asistencia')

            r = c.get(url, {
                'grado': self.grado.id,
                'seccion': self.seccion.id,
            })
            html = r.content.decode('utf-8')
            inicio = html.find('asistencia-actions')
            self.assertNotIn('disabled', html[inicio:inicio + 800])

            r = c.post(url, {
                'grado': self.grado.id,
                'seccion': self.seccion.id,
                'fecha': FECHA_RECORDATORIO.isoformat(),
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-inscripcion': str(self.inscripcion.id),
                'form-0-estado': 'presente',
            })
            self.assertEqual(r.status_code, 302)

            r = c.get(url, {
                'grado': self.grado.id,
                'seccion': self.seccion.id,
            })
            html = r.content.decode('utf-8')
            inicio = html.find('asistencia-actions')
            segmento = html[inicio:inicio + 800]
            self.assertIn('disabled', segmento)
            self.assertIn('opacity-50', segmento)


class CacheAsistenciaTests(TestCase):

    def setUp(self):
        cache.clear()
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 1, 16),
            activo=True
        )

        DiaNoDocencia.objects.create(
            centro=self.centro,
            anio_escolar=self.anio,
            fecha=date(2026, 1, 8),
            motivo='Día de asueto'
        )

        usuario = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='clave123'
        )
        usuario.rol = 'estudiante'
        usuario.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario,
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
            parentesco_tutor='Madre'
        )

        nivel = Nivel.objects.create(centro=self.centro, nombre='Básica')
        grado = Grado.objects.create(nivel=nivel, nombre='1ro')
        seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        grado.secciones.add(seccion)

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=grado,
            seccion=seccion
        )
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(
            fecha=date(2026, 1, 5)
        )
        self.inscripcion.refresh_from_db()

    def registrar_asistencia(self, fecha, estado):
        AsistenciaEstudiante.objects.create(
            inscripcion=self.inscripcion,
            fecha=fecha,
            estado=estado
        )

    def test_resumen_segunda_llamada_sin_consultas(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')
        self.registrar_asistencia(date(2026, 1, 6), 'tardanza')
        self.registrar_asistencia(date(2026, 1, 9), 'ausente')

        primera = resumen_por_inscripciones(
            [self.inscripcion],
            hasta=date(2026, 1, 9),
        )
        self.assertEqual(primera[0]['porcentaje'], 50.0)

        with CaptureQueriesContext(connection) as ctx:
            segunda = resumen_por_inscripciones(
                [self.inscripcion],
                hasta=date(2026, 1, 9),
            )
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[0]['porcentaje'], 50.0)

    def test_registros_del_dia_segunda_llamada_sin_consultas(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')

        primera = registros_del_dia(self.anio, date(2026, 1, 5))
        self.assertEqual(primera[self.inscripcion.id], 'presente')

        with CaptureQueriesContext(connection) as ctx:
            segunda = registros_del_dia(self.anio, date(2026, 1, 5))
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda[self.inscripcion.id], 'presente')

    def test_nueva_asistencia_invalida_resumen(self):
        self.registrar_asistencia(date(2026, 1, 5), 'presente')
        self.registrar_asistencia(date(2026, 1, 6), 'tardanza')
        self.registrar_asistencia(date(2026, 1, 9), 'ausente')

        antes = resumen_por_inscripciones(
            [self.inscripcion],
            hasta=date(2026, 1, 13),
        )
        self.assertEqual(antes[0]['porcentaje'], 33.33)

        self.registrar_asistencia(date(2026, 1, 12), 'presente')

        despues = resumen_por_inscripciones(
            [self.inscripcion],
            hasta=date(2026, 1, 13),
        )
        self.assertEqual(despues[0]['porcentaje'], 50.0)

    def test_eliminar_asistencia_invalida_registros_del_dia(self):
        self.registrar_asistencia(date(2026, 1, 9), 'ausente')

        self.assertEqual(
            registros_del_dia(self.anio, date(2026, 1, 9))[self.inscripcion.id],
            'ausente',
        )

        AsistenciaEstudiante.objects.filter(
            inscripcion=self.inscripcion,
            fecha=date(2026, 1, 9),
        ).delete()

        self.assertNotIn(
            self.inscripcion.id,
            registros_del_dia(self.anio, date(2026, 1, 9)),
        )

    def test_nuevo_dia_no_docencia_invalida_dias_lectivos(self):
        self.assertTrue(es_dia_lectivo(self.anio, date(2026, 1, 12)))

        DiaNoDocencia.objects.create(
            centro=self.centro,
            anio_escolar=self.anio,
            fecha=date(2026, 1, 12),
            motivo='Asueto',
        )

        self.assertFalse(es_dia_lectivo(self.anio, date(2026, 1, 12)))

