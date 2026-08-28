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


