from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academico.models import Grado, Nivel, Seccion
from asistencia.models import AsistenciaEstudiante
from automatizaciones.models import NotificacionAutomatica
from caja.models import ConceptoPago
from comunicaciones.models import Campania
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import Estudiante, Inscripcion
from tutores.models import Tutor
from usuarios.models import Usuario


class BaseAlertasTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001',
        )
        ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_mensajeria=True,
        )
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.director = Usuario.objects.create_user(
            username='director1',
            email='director@test.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

        self.usuario_estudiante = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='clave123',
        )
        self.usuario_estudiante.rol = 'estudiante'
        self.usuario_estudiante.save()

        self.estudiante = Estudiante.objects.create(
            usuario=self.usuario_estudiante,
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
            parentesco_tutor='Madre',
        )

        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Nivel Primario',
            tipo='primaria',
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='1ro',
            orden=1,
        )
        self.seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='A',
        )

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )

        self.tutor = Tutor.objects.create(
            centro=self.centro,
            primer_nombre='María',
            primer_apellido='Pérez',
            cedula='00000000001',
            sexo='F',
            fecha_nacimiento=date(1980, 5, 5),
            nacionalidad='Dominicana',
            telefono='8095550100',
            correo_personal='tutora@test.com',
        )
        self.tutor.estudiantes.add(self.estudiante)

        self.concepto_recurrente = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )

    def instalar_vecindad(self, estados):
        hoy = timezone.localdate()
        for indice, estado in enumerate(estados):
            AsistenciaEstudiante.objects.create(
                inscripcion=self.inscripcion,
                fecha=hoy - timedelta(days=indice),
                estado=estado,
            )

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()


class TableroVistaTestCase(BaseAlertasTestCase):

    def test_tablero_permitido_para_director(self):
        self.login(self.director)
        response = self.client.get(reverse('automatizaciones:tablero'))
        self.assertEqual(response.status_code, 200)

    def test_tablero_denegado_para_estudiante(self):
        self.login(self.usuario_estudiante)
        response = self.client.get(reverse('automatizaciones:tablero'))
        self.assertEqual(response.status_code, 403)

    def test_inasistencias_no_alarma_con_asistencia(self):
        self.instalar_vecindad(['presente', 'presente'])
        self.login(self.director)
        response = self.client.get(reverse('automatizaciones:tablero'))
        self.assertContains(response, 'Inasistencias consecutivas')
        self.assertContains(response, 'Sin novedades')

    def test_inasistencias_alarma_con_tres_faltas(self):
        self.instalar_vecindad(['ausente', 'ausente', 'ausente'])
        self.login(self.director)
        response = self.client.get(reverse('automatizaciones:tablero'))
        self.assertContains(response, '3 ausencias consecutivas')


class CrearCampaniaTestCase(BaseAlertasTestCase):

    def test_regla_invalida_redirige(self):
        self.login(self.director)
        campanias = Campania.objects.count()
        response = self.client.post(
            reverse('automatizaciones:crear_campania'),
            {'regla': 'no-existe'},
        )
        self.assertRedirects(response, reverse('automatizaciones:tablero'))
        self.assertEqual(Campania.objects.count(), campanias)

    def test_crea_campania_y_registra_notificacion(self):
        self.instalar_vecindad(['ausente', 'ausente', 'ausente'])
        self.login(self.director)

        response = self.client.post(
            reverse('automatizaciones:crear_campania'),
            {'regla': 'inasistencias'},
        )

        campania = Campania.objects.get()
        self.assertRedirects(
            response,
            reverse('comunicaciones:campania_detail', args=[campania.pk]),
        )
        self.assertEqual(campania.estado, 'borrador')
        self.assertIn(self.tutor, campania.tutores.all())

        notificacion = NotificacionAutomatica.objects.get()
        self.assertEqual(notificacion.tipo, 'inasistencias')
        self.assertEqual(notificacion.campania, campania)

    def test_sin_datos_no_crea_campania(self):
        self.login(self.director)
        campanias = Campania.objects.count()
        response = self.client.post(
            reverse('automatizaciones:crear_campania'),
            {'regla': 'cumpleanos'},
        )
        self.assertRedirects(response, reverse('automatizaciones:tablero'))
        self.assertEqual(Campania.objects.count(), campanias)
        self.assertEqual(NotificacionAutomatica.objects.count(), 0)

    def test_accion_solo_por_post(self):
        self.login(self.director)
        campanias = Campania.objects.count()
        response = self.client.get(
            reverse('automatizaciones:crear_campania'),
            {'regla': 'inasistencias'},
        )
        self.assertRedirects(response, reverse('automatizaciones:tablero'))
        self.assertEqual(Campania.objects.count(), campanias)