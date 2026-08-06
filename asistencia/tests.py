from datetime import date

from django.test import TestCase

from academico.models import Grado, Nivel, Seccion
from asistencia.models import AsistenciaEstudiante, DiaNoDocencia
from asistencia.services import (
    calcular_promedio_inscripcion,
    dias_lectivos,
    es_dia_lectivo,
    resumen_por_inscripciones,
)
from core.models import AnioEscolar, CentroEducativo
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario


class AsistenciaServicesTestCase(TestCase):

    def setUp(self):
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
        seccion = Seccion.objects.create(grado=grado, nombre='A')

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
