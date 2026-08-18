from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from caja.models import AsignacionConcepto, ConceptoPago, Pago
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import Estudiante, HistorialClinicoEstudiante, RegistroSalud, SolicitudCertificado
from tutores.models import Tutor
from usuarios.models import Usuario


class TutorSolicitudesTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0002'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_certificados=True,
            precio_certificado=450,
        )

        self.tutor_usuario = Usuario.objects.create_user(
            username='tutor1',
            email='tutor1@test.com',
            password='clave123'
        )
        self.tutor_usuario.rol = 'tutor'
        self.tutor_usuario.save()

        self.tutor = Tutor.objects.create(
            usuario=self.tutor_usuario,
            centro=self.centro,
            cedula='00100000007',
            primer_nombre='Pedro',
            primer_apellido='Martinez',
            fecha_nacimiento='1980-04-15',
            correo_personal='pedro@test.com',
            telefono='809-555-0107',
        )

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='estt1',
                email='estt1@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260010',
            primer_nombre='Sofia',
            primer_apellido='Martinez',
            sexo='F',
            fecha_nacimiento='2010-09-05',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 10',
            nombre_tutor='Pedro Martinez',
            cedula_tutor='00100000007',
            telefono_tutor='809-555-0107',
            parentesco_tutor='Padre',
        )
        self.estudiante.usuario.rol = 'estudiante'
        self.estudiante.usuario.save()
        self.estudiante.tutores.add(self.tutor)

    def _login(self):
        self.client.login(username='tutor1', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _solicitar(self, estudiante_id, tipo='constancia_conducta'):
        return self.client.post(
            '/tutores/inicio/solicitudes/',
            {
                'estudiante': estudiante_id,
                'tipo_certificado': tipo,
                'metodo_pago': 'efectivo',
                'motivo': 'Para trabajo',
            },
            follow=True
        )

    def test_tutor_solicita_para_su_estudiante(self):
        self._login()

        response = self._solicitar(self.estudiante.id)

        self.assertEqual(response.status_code, 200)
        solicitud = SolicitudCertificado.objects.get(
            estudiante=self.estudiante
        )
        self.assertEqual(solicitud.solicitante, self.tutor_usuario)
        self.assertEqual(solicitud.monto, 450)
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_tutor_no_puede_solicitar_para_estudiante_ajeno(self):
        otro_usuario = Usuario.objects.create_user(
            username='estt2',
            email='estt2@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        ajeno = Estudiante.objects.create(
            usuario=otro_usuario,
            centro=self.centro,
            matricula='20260011',
            primer_nombre='Juan',
            primer_apellido='Lara',
            sexo='M',
            fecha_nacimiento='2010-11-11',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 11',
            nombre_tutor='Otro',
            cedula_tutor='00100000008',
            telefono_tutor='809-555-0108',
            parentesco_tutor='Madre',
        )

        self._login()

        self._solicitar(ajeno.id)

        self.assertFalse(
            SolicitudCertificado.objects.filter(
                estudiante=ajeno
            ).exists()
        )

    def test_lista_muestra_solo_sus_estudiantes(self):
        self._login()
        self._solicitar(self.estudiante.id)

        response = self.client.get('/tutores/inicio/solicitudes/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())
        self.assertContains(response, 'SC-')

    def test_tutor_sin_estudiantes_no_rompe(self):
        self._login()

        response = self.client.get('/tutores/inicio/solicitudes/')

        self.assertEqual(response.status_code, 200)


class TutorHistorialClinicoTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0004'
        )

        self.tutor_usuario = Usuario.objects.create_user(
            username='tutorhc',
            email='tutorhc@test.com',
            password='clave123'
        )
        self.tutor_usuario.rol = 'tutor'
        self.tutor_usuario.save()

        self.tutor = Tutor.objects.create(
            usuario=self.tutor_usuario,
            centro=self.centro,
            cedula='00100000022',
            primer_nombre='Maria',
            primer_apellido='Fernandez',
            fecha_nacimiento='1982-03-12',
            correo_personal='maria@test.com',
            telefono='809-555-0122',
        )

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='esthct1',
                email='esthct1@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260030',
            primer_nombre='Diego',
            primer_apellido='Fernandez',
            sexo='M',
            fecha_nacimiento='2010-08-20',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 30',
            nombre_tutor='Maria Fernandez',
            cedula_tutor='00100000022',
            telefono_tutor='809-555-0122',
            parentesco_tutor='Madre',
        )
        self.estudiante.usuario.rol = 'estudiante'
        self.estudiante.usuario.save()
        self.estudiante.tutores.add(self.tutor)

        self.historial = HistorialClinicoEstudiante.objects.create(
            estudiante=self.estudiante,
            grupo_sanguineo='B-',
            alergias='Polvo',
            condiciones_medicas='Rinitis',
            contacto_emergencia_nombre='Maria Fernandez',
            contacto_emergencia_telefono='809-555-0122',
        )

        RegistroSalud.objects.create(
            estudiante=self.estudiante,
            tipo='enfermedad',
            fecha='2026-02-10',
            descripcion='Rinitis alérgica',
            notificado_a_tutor=True,
            registrado_por=self.tutor_usuario,
        )

    def _login(self):
        self.client.login(username='tutorhc', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_tutor_ve_historial_de_sus_estudiantes(self):
        self._login()

        response = self.client.get('/tutores/inicio/historial-clinico/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())
        self.assertContains(response, 'B-')
        self.assertContains(response, 'Polvo')
        self.assertContains(response, 'Maria Fernandez')
        self.assertContains(response, 'Rinitis alérgica')

    def test_tutor_no_ve_estudiante_ajeno(self):
        otro_usuario = Usuario.objects.create_user(
            username='esthct2',
            email='esthct2@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        ajeno = Estudiante.objects.create(
            usuario=otro_usuario,
            centro=self.centro,
            matricula='20260031',
            primer_nombre='Paola',
            primer_apellido='Gonzalez',
            sexo='F',
            fecha_nacimiento='2010-01-25',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 31',
            nombre_tutor='Otro',
            cedula_tutor='00100000023',
            telefono_tutor='809-555-0123',
            parentesco_tutor='Madre',
        )

        HistorialClinicoEstudiante.objects.create(
            estudiante=ajeno,
            grupo_sanguineo='A+',
            alergias='Mariscos',
            contacto_emergencia_nombre='Otro Tutor',
        )

        self._login()

        response = self.client.get('/tutores/inicio/historial-clinico/')

        self.assertNotContains(response, 'Paola Gonzalez')
        self.assertNotContains(response, 'Mariscos')

    def test_tutor_sin_estudiantes_no_rompe(self):
        self.estudiante.tutores.clear()

        self._login()

        response = self.client.get('/tutores/inicio/historial-clinico/')

        self.assertEqual(response.status_code, 200)

    def test_tutor_selecciona_estudiante_y_ve_su_historial(self):
        self._login()

        response = self.client.get(
            f'/tutores/inicio/historial-clinico/?estudiante={self.estudiante.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())
        self.assertContains(response, 'B-')
        self.assertContains(response, 'Polvo')
        self.assertContains(response, 'Rinitis alérgica')

    def test_tutor_no_puede_ver_historial_de_estudiante_ajeno_por_parametro(self):
        otro_usuario = Usuario.objects.create_user(
            username='esthct3',
            email='esthct3@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        ajeno = Estudiante.objects.create(
            usuario=otro_usuario,
            centro=self.centro,
            matricula='20260032',
            primer_nombre='Rosa',
            primer_apellido='Peralta',
            sexo='F',
            fecha_nacimiento='2010-03-30',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 32',
            nombre_tutor='Otro',
            cedula_tutor='00100000024',
            telefono_tutor='809-555-0124',
            parentesco_tutor='Madre',
        )

        self._login()

        response = self.client.get(
            f'/tutores/inicio/historial-clinico/?estudiante={ajeno.id}'
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_tutor_ve_mensaje_si_estudiante_no_tiene_historial(self):
        sin_historial_usuario = Usuario.objects.create_user(
            username='esthct4',
            email='esthct4@test.com',
            password='clave123'
        )
        sin_historial_usuario.rol = 'estudiante'
        sin_historial_usuario.save()

        sin_historial = Estudiante.objects.create(
            usuario=sin_historial_usuario,
            centro=self.centro,
            matricula='20260033',
            primer_nombre='Luis',
            primer_apellido='Perez',
            sexo='M',
            fecha_nacimiento='2010-04-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 33',
            nombre_tutor='Otro',
            cedula_tutor='00100000025',
            telefono_tutor='809-555-0125',
            parentesco_tutor='Padre',
        )
        sin_historial.tutores.add(self.tutor)

        self._login()

        response = self.client.get(
            f'/tutores/inicio/historial-clinico/?estudiante={sin_historial.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'No se ha registrado historial clínico'
        )


class CacheTutoresTests(TestCase):

    def setUp(self):
        from datetime import date

        from django.core.cache import cache

        from academico.models import Grado, Nivel, Seccion
        from core.models import AnioEscolar

        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0005'
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 12, 31),
            activo=True
        )

        self.tutor_usuario = Usuario.objects.create_user(
            username='tutcache',
            email='tutcache@test.com',
            password='clave123'
        )
        self.tutor_usuario.rol = 'tutor'
        self.tutor_usuario.save()

        self.tutor = Tutor.objects.create(
            usuario=self.tutor_usuario,
            centro=self.centro,
            cedula='00100000030',
            primer_nombre='Pedro',
            primer_apellido='Martinez',
            fecha_nacimiento='1980-04-15',
            correo_personal='pedro@test.com',
            telefono='809-555-0130',
        )

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='estcache1',
                email='estcache1@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260040',
            primer_nombre='Sofia',
            primer_apellido='Martinez',
            sexo='F',
            fecha_nacimiento='2010-09-05',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 40',
            nombre_tutor='Pedro Martinez',
            cedula_tutor='00100000030',
            telefono_tutor='809-555-0130',
            parentesco_tutor='Padre',
        )
        self.estudiante.usuario.rol = 'estudiante'
        self.estudiante.usuario.save()

        nivel = Nivel.objects.create(centro=self.centro, nombre='Primaria')
        self.grado = Grado.objects.create(nivel=nivel, nombre='1ro')
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.grado.secciones.add(self.seccion)

    def test_lista_segunda_llamada_sin_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from tutores.services import tutores_del_centro

        self.estudiante.tutores.add(self.tutor)

        primera = tutores_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = tutores_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nuevo_tutor_invalida_lista(self):
        from tutores.services import tutores_del_centro

        self.estudiante.tutores.add(self.tutor)

        antes = tutores_del_centro(self.centro)
        self.assertEqual(len(antes), 1)

        otro = Usuario.objects.create_user(
            username='tutcache2',
            email='tutcache2@test.com',
            password='clave123'
        )
        otro.rol = 'tutor'
        otro.save()

        Tutor.objects.create(
            usuario=otro,
            centro=self.centro,
            cedula='00100000031',
            primer_nombre='Luis',
            primer_apellido='Perez',
            fecha_nacimiento='1985-01-01',
            correo_personal='luis@test.com',
            telefono='809-555-0131',
        )

        despues = tutores_del_centro(self.centro)
        self.assertEqual(len(despues), 2)

    def test_agregar_estudiante_invalida_lista(self):
        from tutores.services import tutores_del_centro

        antes = tutores_del_centro(self.centro)
        self.assertEqual(len(antes[0].estudiantes.all()), 0)

        self.estudiante.tutores.add(self.tutor)

        despues = tutores_del_centro(self.centro)
        self.assertEqual(len(despues[0].estudiantes.all()), 1)

    def test_panel_segunda_llamada_sin_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from tutores.services import datos_inicio_tutor

        self.estudiante.tutores.add(self.tutor)

        from estudiantes.models import Inscripcion

        Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion
        )

        primera = datos_inicio_tutor(self.tutor)
        self.assertEqual(len(primera), 1)
        self.assertIsNotNone(primera[0]['inscripcion_actual'])

        with CaptureQueriesContext(connection) as ctx:
            segunda = datos_inicio_tutor(self.tutor)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_inscripcion_nueva_actualiza_panel(self):
        from tutores.services import datos_inicio_tutor

        self.estudiante.tutores.add(self.tutor)

        antes = datos_inicio_tutor(self.tutor)
        self.assertIsNone(antes[0]['inscripcion_actual'])

        from estudiantes.models import Inscripcion

        Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion
        )

        despues = datos_inicio_tutor(self.tutor)
        self.assertIsNotNone(despues[0]['inscripcion_actual'])


class DeudaTutorTests(TestCase):

    HOY = date(2026, 8, 15)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0005'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_certificados=True,
            precio_certificado=450,
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.tutor_usuario = Usuario.objects.create_user(
            username='tutordeb',
            email='tutordeb@test.com',
            password='clave123'
        )
        self.tutor_usuario.rol = 'tutor'
        self.tutor_usuario.save()

        self.tutor = Tutor.objects.create(
            usuario=self.tutor_usuario,
            centro=self.centro,
            cedula='00100000009',
            primer_nombre='Luis',
            primer_apellido='Fernandez',
            fecha_nacimiento='1978-05-10',
            correo_personal='luis@test.com',
            telefono='809-555-0109',
        )

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='estdeb',
                email='estdeb@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260012',
            primer_nombre='Maria',
            primer_apellido='Fernandez',
            sexo='F',
            fecha_nacimiento='2010-09-05',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 12',
            nombre_tutor='Luis Fernandez',
            cedula_tutor='00100000009',
            telefono_tutor='809-555-0109',
            parentesco_tutor='Padre',
        )
        self.estudiante.usuario.rol = 'estudiante'
        self.estudiante.usuario.save()
        self.estudiante.tutores.add(self.tutor)

        self.concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )

    def _login(self):
        self.client.login(username='tutordeb', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _con_deuda(self):
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )

    def _al_dia(self):
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )
        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('15000.00'),
            recibo=1,
            fecha=self.HOY,
        )

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_inicio_muestra_card_con_deuda(self, _hoy):
        self._con_deuda()
        self._login()

        response = self.client.get('/tutores/inicio/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado de mis deudas')
        self.assertContains(response, 'Vencida')
        self.assertContains(response, 'Próximo a vencer')
        self.assertContains(response, 'RD$ 10,000')
        self.assertContains(response, 'RD$ 5,000')

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_inicio_al_dia_muestra_mensaje(self, _hoy):
        self._al_dia()
        self._login()

        response = self.client.get('/tutores/inicio/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estás al día')

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_solicitud_con_deuda_se_bloquea(self, _hoy):
        self._con_deuda()
        self._login()

        response = self.client.post(
            '/tutores/inicio/solicitudes/',
            {
                'estudiante': self.estudiante.id,
                'tipo_certificado': 'constancia_conducta',
                'metodo_pago': 'efectivo',
                'motivo': 'Para trabajo',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tiene deuda pendiente')
        self.assertFalse(
            SolicitudCertificado.objects.filter(
                estudiante=self.estudiante
            ).exists()
        )

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_solicitud_sin_deuda_se_registra(self, _hoy):
        self._al_dia()
        self._login()

        response = self.client.post(
            '/tutores/inicio/solicitudes/',
            {
                'estudiante': self.estudiante.id,
                'tipo_certificado': 'constancia_conducta',
                'metodo_pago': 'efectivo',
                'motivo': 'Para trabajo',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            SolicitudCertificado.objects.filter(
                estudiante=self.estudiante
            ).exists()
        )
