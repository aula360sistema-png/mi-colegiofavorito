from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from academico.models import (
    AreaCurricular,
    Asignatura,
    DocenteMateria,
    FranjaHoraria,
    Grado,
    HorarioClase,
    Nivel,
    Seccion,
)
from administracion.models import Administrativo
from core.models import AnioEscolar, CentroEducativo
from docentes.models import Docente
from usuarios.models import Usuario


class HorarioTestCase(TestCase):

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

        usuario = Usuario.objects.create_user(
            username='director',
            email='director@test.com',
            password='clave123'
        )
        usuario.rol = 'director'
        usuario.save()

        Administrativo.objects.create(
            usuario=usuario,
            centro=self.centro,
            primer_nombre='Ana',
            primer_apellido='García',
            cedula='00100000000',
            sexo='F',
            fecha_nacimiento=date(1980, 1, 1),
            nacionalidad='Dominicana',
            direccion='Calle 1',
            telefono='8090000000',
            cargo='director',
            fecha_ingreso=date(2020, 1, 1),
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

        self.seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='A'
        )
        self.grado.secciones.add(self.seccion)

        self.area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Lengua'
        )

        self.asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=self.area,
            nombre='Español'
        )

        self.docente = Docente.objects.create(
            centro=self.centro,
            primer_nombre='María',
            primer_apellido='López',
            cedula='00200000000',
            sexo='F',
            fecha_nacimiento=date(1985, 1, 1),
            nacionalidad='Dominicana',
            direccion='Calle 2',
            telefono='8091111111',
            codigo_docente_minerd='DOC-0001',
            area_especialidad='Lengua',
            fecha_ingreso=date(2021, 1, 1),
            tipo_contrato='contratado',
            tanda='matutina',
            estado='activo'
        )

        self.asignacion = DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio
        )

        self.franja = FranjaHoraria.objects.create(
            centro=self.centro,
            nombre='1ra hora',
            hora_inicio=time(7, 30),
            hora_fin=time(8, 20),
            orden=1
        )

        self.client.force_login(usuario)

    def test_franja_create(self):
        response = self.client.post(reverse('franja_create'), {
            'nombre': '2da hora',
            'hora_inicio': '08:20',
            'hora_fin': '09:10',
            'orden': 2,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FranjaHoraria.objects.filter(
            centro=self.centro,
            nombre='2da hora'
        ).exists())

    def test_franja_create_duplicada(self):
        response = self.client.post(reverse('franja_create'), {
            'nombre': '1ra hora',
            'hora_inicio': '08:20',
            'hora_fin': '09:10',
            'orden': 2,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una franja')

    def test_horario_list_sin_seleccion(self):
        response = self.client.get(reverse('horario_list'))
        self.assertEqual(response.status_code, 200)

    def test_horario_list_con_seleccion(self):
        response = self.client.get(reverse('horario_list'), {
            'grado': self.grado.id,
            'seccion': self.seccion.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Español')

    def test_horario_clase_create(self):
        response = self.client.post(reverse('horario_clase_create'), {
            'asignacion': self.asignacion.id,
            'dia_semana': 1,
            'franja': self.franja.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HorarioClase.objects.filter(
            asignacion=self.asignacion,
            dia_semana=1,
            franja=self.franja
        ).exists())

    def test_horario_clase_choque_seccion(self):
        HorarioClase.objects.create(
            asignacion=self.asignacion,
            dia_semana=1,
            franja=self.franja
        )

        otro_docente = Docente.objects.create(
            centro=self.centro,
            primer_nombre='Luis',
            primer_apellido='Martínez',
            cedula='00300000000',
            sexo='M',
            fecha_nacimiento=date(1985, 1, 1),
            nacionalidad='Dominicana',
            direccion='Calle 3',
            telefono='8092222222',
            codigo_docente_minerd='DOC-0002',
            area_especialidad='Matemática',
            fecha_ingreso=date(2021, 1, 1),
            tipo_contrato='contratado',
            tanda='matutina',
            estado='activo'
        )

        otra_area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Matemática'
        )

        otra_asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=otra_area,
            nombre='Matemáticas'
        )

        otra_asignacion = DocenteMateria.objects.create(
            docente=otro_docente,
            asignatura=otra_asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio
        )

        response = self.client.post(reverse('horario_clase_create'), {
            'asignacion': otra_asignacion.id,
            'dia_semana': 1,
            'franja': self.franja.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ya tiene otra materia')

    def test_horario_clase_delete(self):
        clase = HorarioClase.objects.create(
            asignacion=self.asignacion,
            dia_semana=1,
            franja=self.franja
        )
        response = self.client.post(
            reverse('horario_clase_delete', args=[clase.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HorarioClase.objects.filter(pk=clase.pk).exists())
