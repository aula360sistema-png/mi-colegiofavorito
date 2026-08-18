from datetime import date

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from academico.models import (
    AreaCurricular,
    Asignatura,
    DocenteMateria,
    Grado,
    Nivel,
    Seccion,
)
from core.models import AnioEscolar, CentroEducativo
from docentes.models import Docente
from docentes.services import datos_dashboard_docente, docentes_del_centro
from estudiantes.models import Inscripcion
from usuarios.models import Usuario


class CacheDocentesTests(TestCase):

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
            fecha_fin=date(2026, 12, 31),
            activo=True
        )

        usuario = Usuario.objects.create_user(
            username='doc1',
            email='doc1@test.com',
            password='clave123'
        )
        usuario.rol = 'docente'
        usuario.save()

        self.docente = Docente.objects.create(
            usuario=usuario,
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

        nivel = Nivel.objects.create(centro=self.centro, nombre='Primaria')
        self.grado = Grado.objects.create(nivel=nivel, nombre='1ro')
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.grado.secciones.add(self.seccion)

        area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Ciencias'
        )
        self.asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=area,
            nombre='Matemática'
        )

        self.asignacion = DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio
        )

    def test_docentes_lista_segunda_llamada_sin_consultas(self):
        primera = docentes_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = docentes_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nuevo_docente_invalida_lista(self):
        antes = docentes_del_centro(self.centro)
        self.assertEqual(len(antes), 1)

        otro = Usuario.objects.create_user(
            username='doc2',
            email='doc2@test.com',
            password='clave123'
        )
        otro.rol = 'docente'
        otro.save()

        Docente.objects.create(
            usuario=otro,
            centro=self.centro,
            primer_nombre='Luis',
            primer_apellido='Perez',
            cedula='22222222222',
            sexo='M',
            fecha_nacimiento=date(1985, 1, 1),
            nacionalidad='Dominicana',
            direccion='Calle 2',
            telefono='8091111111',
            codigo_docente_minerd='D2',
            area_especialidad='Español',
            fecha_ingreso=date(2015, 1, 1),
            tipo_contrato='contratado',
            tanda='vespertina'
        )

        despues = docentes_del_centro(self.centro)
        self.assertEqual(len(despues), 2)

    def test_dashboard_segunda_llamada_sin_consultas(self):
        primera = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(primera['total_asignaciones'], 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(segunda['total_asignaciones'], 1)

    def test_nueva_asignacion_invalida_dashboard(self):
        antes = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(antes['total_asignaciones'], 1)

        grado2 = Grado.objects.create(nivel=self.grado.nivel, nombre='2do')
        seccion2 = Seccion.objects.create(centro=self.centro, nombre='B')
        grado2.secciones.add(seccion2)

        DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=grado2,
            seccion=seccion2,
            anio_escolar=self.anio
        )

        despues = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(despues['total_asignaciones'], 2)

    def test_inscripcion_invalida_conteo_del_dashboard(self):
        primero = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(primero['total_estudiantes'], 0)

        usuario_est = Usuario.objects.create_user(
            username='est1',
            email='est1@test.com',
            password='clave123'
        )
        usuario_est.rol = 'estudiante'
        usuario_est.save()

        from estudiantes.models import Estudiante

        estudiante = Estudiante.objects.create(
            usuario=usuario_est,
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

        Inscripcion.objects.create(
            estudiante=estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion
        )

        despues = datos_dashboard_docente(self.docente, self.anio)
        self.assertEqual(despues['total_estudiantes'], 1)
