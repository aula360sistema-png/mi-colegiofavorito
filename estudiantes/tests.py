from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from academico.models import Grado, Nivel, Seccion
from caja.models import AsignacionConcepto, ConceptoPago
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import (
    DocumentoEstudiante,
    Estudiante,
    HistorialClinicoEstudiante,
    Inscripcion,
    ObservacionEstudiante,
    RegistroSalud,
    SolicitudCertificado,
)
from usuarios.models import Usuario
from tutores.models import Tutor


class DocumentoEstudianteTests(TestCase):
    def _documento(self, nombre, contenido, content_type):
        doc = DocumentoEstudiante(nombre=nombre)
        doc.archivo = SimpleUploadedFile(nombre, contenido, content_type=content_type)
        return doc

    def test_rechaza_archivo_no_permitido(self):
        doc = self._documento(
            "malware.exe", b"datos", content_type="application/octet-stream",
        )
        with self.assertRaises(ValidationError):
            doc.full_clean(exclude=["estudiante", "fecha_subida"])

    def test_acepta_pdf(self):
        doc = self._documento(
            "acta.pdf", b"%PDF-1.4", content_type="application/pdf",
        )
        doc.full_clean(exclude=["estudiante", "fecha_subida"])


class DisciplinaTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.director = Usuario.objects.create_user(
            username='director',
            email='director@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='est1',
                email='est1@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260001',
            primer_nombre='Ana',
            primer_apellido='Perez',
            sexo='F',
            fecha_nacimiento='2010-05-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle Prueba',
            nombre_tutor='Tutor',
            cedula_tutor='00100000003',
            telefono_tutor='809-555-0103',
            parentesco_tutor='Madre',
        )
        self.estudiante.usuario.rol = 'estudiante'
        self.estudiante.usuario.save()

    def _login(self):
        self.client.login(username='director', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _registrar(self, tipo='amonestacion'):
        return self.client.post(
            '/estudiantes/disciplina/registrar/',
            {
                'estudiante': self.estudiante.id,
                'tipo': tipo,
                'fecha': '2026-08-01',
                'descripcion': 'Llegada tarde repetida.',
            },
            follow=True
        )

    def test_disciplina_lista_vacia(self):
        self._login()

        response = self.client.get('/estudiantes/disciplina/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay registros de disciplina')

    def test_registrar_amonestacion(self):
        self._login()

        response = self._registrar('amonestacion')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ObservacionEstudiante.objects.filter(
                estudiante=self.estudiante,
                tipo='amonestacion'
            ).exists()
        )

    def test_registrar_merito(self):
        self._login()

        self._registrar('merito')

        self.assertTrue(
            ObservacionEstudiante.objects.filter(
                estudiante=self.estudiante,
                tipo='merito'
            ).exists()
        )

    def test_lista_muestra_registros(self):
        self._login()
        self._registrar()

        response = self.client.get('/estudiantes/disciplina/')

        self.assertContains(response, 'Llegada tarde repetida')
        self.assertContains(response, '20260001')

    def test_filtro_por_tipo(self):
        self._login()
        self._registrar('amonestacion')

        response = self.client.get('/estudiantes/disciplina/', {'tipo': 'merito'})

        self.assertContains(response, 'No hay registros de disciplina')

        response = self.client.get('/estudiantes/disciplina/', {'tipo': 'amonestacion'})

        self.assertContains(response, 'Llegada tarde repetida')

    def test_busqueda_por_matricula(self):
        self._login()
        self._registrar()

        response = self.client.get('/estudiantes/disciplina/', {'q': '20260001'})

        self.assertContains(response, 'Llegada tarde repetida')

    def test_eliminar_registro(self):
        self._login()
        self._registrar()

        obs = ObservacionEstudiante.objects.get(estudiante=self.estudiante)

        response = self.client.post(
            f'/estudiantes/disciplina/{obs.id}/eliminar/',
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ObservacionEstudiante.objects.filter(pk=obs.id).exists()
        )

    def test_rol_sin_acceso_bloqueado(self):
        otro = Usuario.objects.create_user(
            username='estudiantefake',
            email='fake@test.com',
            password='clave123'
        )
        otro.rol = 'estudiante'
        otro.save()
        self.client.login(username='estudiantefake', password='clave123')

        response = self.client.get('/estudiantes/disciplina/')

        self.assertNotEqual(response.status_code, 200)


class SolicitudCertificadoTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_certificados=True,
            modulo_caja=True,
            precio_certificado=500,
            permitir_pago_online=True,
        )

        usuario_estudiante = Usuario.objects.create_user(
            username='est2',
            email='est2@test.com',
            password='clave123'
        )
        usuario_estudiante.rol = 'estudiante'
        usuario_estudiante.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario_estudiante,
            centro=self.centro,
            matricula='20260002',
            primer_nombre='Luis',
            primer_apellido='Gomez',
            sexo='M',
            fecha_nacimiento='2011-01-15',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 2',
            nombre_tutor='Tutor',
            cedula_tutor='00100000004',
            telefono_tutor='809-555-0104',
            parentesco_tutor='Padre',
        )

        self.director = Usuario.objects.create_user(
            username='director2',
            email='director2@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

    def _login_estudiante(self):
        self.client.login(username='est2', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _solicitar(self, tipo='constancia_estudio', metodo='online', motivo='Para trabajo'):
        return self.client.post(
            '/estudiantes/inicio/solicitudes/',
            {
                'tipo_certificado': tipo,
                'metodo_pago': metodo,
                'motivo': motivo,
            },
            follow=True
        )

    def test_solicitud_asigna_folio(self):
        self._login_estudiante()

        self._solicitar()

        solicitud = SolicitudCertificado.objects.get(estudiante=self.estudiante)

        self.assertTrue(solicitud.folio.startswith('SC-'))
        self.assertEqual(solicitud.monto, 500)
        self.assertEqual(solicitud.solicitante, self.estudiante.usuario)
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_solicitud_folio_incrementa(self):
        self._login_estudiante()

        self._solicitar()
        self._solicitar()

        folios = sorted(
            SolicitudCertificado.objects.values_list('folio', flat=True)
        )
        self.assertNotEqual(folios[0], folios[1])

    def test_pago_online_marca_pagada(self):
        self._login_estudiante()
        self._solicitar()

        solicitud = SolicitudCertificado.objects.get(estudiante=self.estudiante)

        response = self.client.get(
            f'/estudiantes/inicio/solicitudes/{solicitud.pk}/pagar/',
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.pagado)
        self.assertEqual(solicitud.estado, 'pagada')
        self.assertTrue(solicitud.referencia_pago.startswith('ONL-'))

    def test_modulo_desactivado_bloquea_solicitud(self):
        self.config.modulo_certificados = False
        self.config.save()

        self._login_estudiante()
        self._solicitar()

        self.assertFalse(
            SolicitudCertificado.objects.filter(
                estudiante=self.estudiante
            ).exists()
        )

    def test_pago_online_desactivado_devuelve_error(self):
        self.config.permitir_pago_online = False
        self.config.save()

        self._login_estudiante()
        self._solicitar()

        solicitud = SolicitudCertificado.objects.get(estudiante=self.estudiante)

        self.client.get(
            f'/estudiantes/inicio/solicitudes/{solicitud.pk}/pagar/',
            follow=True
        )

        solicitud.refresh_from_db()
        self.assertFalse(solicitud.pagado)
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_estudiante_no_puede_ver_otros(self):
        otro_usuario = Usuario.objects.create_user(
            username='est3',
            email='est3@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        Estudiante.objects.create(
            usuario=otro_usuario,
            centro=self.centro,
            matricula='20260003',
            primer_nombre='Maria',
            primer_apellido='Diaz',
            sexo='F',
            fecha_nacimiento='2010-03-20',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 3',
            nombre_tutor='Tutor',
            cedula_tutor='00100000005',
            telefono_tutor='809-555-0105',
            parentesco_tutor='Madre',
        )

        solicitud = SolicitudCertificado.objects.create(
            folio='SC-2026-9999',
            estudiante=Estudiante.objects.get(matricula='20260003'),
            solicitante=otro_usuario,
            tipo_certificado='constancia_estudio',
            monto=500,
        )

        self._login_estudiante()

        response = self.client.get('/estudiantes/inicio/solicitudes/')

        self.assertNotContains(response, solicitud.folio)

    def test_pago_online_solo_su_solicitud(self):
        otro_usuario = Usuario.objects.create_user(
            username='est4',
            email='est4@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        Estudiante.objects.create(
            usuario=otro_usuario,
            centro=self.centro,
            matricula='20260004',
            primer_nombre='Carlos',
            primer_apellido='Lopez',
            sexo='M',
            fecha_nacimiento='2010-07-01',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 4',
            nombre_tutor='Tutor',
            cedula_tutor='00100000006',
            telefono_tutor='809-555-0106',
            parentesco_tutor='Padre',
        )

        solicitud_ajena = SolicitudCertificado.objects.create(
            folio='SC-2026-9998',
            estudiante=Estudiante.objects.get(matricula='20260004'),
            solicitante=otro_usuario,
            tipo_certificado='record_notas',
            monto=500,
        )

        self._login_estudiante()

        response = self.client.get(
            f'/estudiantes/inicio/solicitudes/{solicitud_ajena.pk}/pagar/',
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        solicitud_ajena.refresh_from_db()
        self.assertFalse(solicitud_ajena.pagado)
        self.assertEqual(solicitud_ajena.estado, 'pendiente')


class HistorialClinicoTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0003'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro
        )

        usuario_estudiante = Usuario.objects.create_user(
            username='esthc1',
            email='esthc1@test.com',
            password='clave123'
        )
        usuario_estudiante.rol = 'estudiante'
        usuario_estudiante.save()

        self.estudiante = Estudiante.objects.create(
            usuario=usuario_estudiante,
            centro=self.centro,
            matricula='20260020',
            primer_nombre='Ana',
            primer_apellido='Perez',
            sexo='F',
            fecha_nacimiento='2011-05-10',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 20',
            nombre_tutor='Tutor',
            cedula_tutor='00100000020',
            telefono_tutor='809-555-0120',
            parentesco_tutor='Madre',
        )

        self.director = Usuario.objects.create_user(
            username='directorhc',
            email='directorhc@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

    def _login_estudiante(self):
        self.client.login(username='esthc1', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _login_director(self):
        self.client.login(username='directorhc', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _crear_historial(self):
        return HistorialClinicoEstudiante.objects.create(
            estudiante=self.estudiante,
            grupo_sanguineo='O+',
            alergias='Penicilina',
            condiciones_medicas='Asma',
            medicamentos_habituales='Salbutamol',
            contacto_emergencia_nombre='Maria Perez',
            contacto_emergencia_telefono='809-555-0199',
            contacto_emergencia_parentesco='Madre',
        )

    def test_estudiante_ve_su_historial(self):
        historial = self._crear_historial()
        self._login_estudiante()

        response = self.client.get('/estudiantes/inicio/historial-clinico/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O+')
        self.assertContains(response, 'Penicilina')
        self.assertContains(response, 'Maria Perez')

    def test_estudiante_ve_historial_creado_auto(self):
        self._login_estudiante()

        response = self.client.get('/estudiantes/inicio/historial-clinico/')

        self.assertEqual(response.status_code, 200)
        historial = HistorialClinicoEstudiante.objects.get(
            estudiante=self.estudiante
        )
        self.assertContains(response, historial.get_grupo_sanguineo_display())

    def test_estudiante_ve_sus_registros_de_salud(self):
        self._crear_historial()
        RegistroSalud.objects.create(
            estudiante=self.estudiante,
            tipo='enfermedad',
            fecha='2026-03-10',
            descripcion='Gripe con fiebre',
            atencion_proporcionada='Reposo y líquidos',
            notificado_a_tutor=True,
            registrado_por=self.director,
        )
        self._login_estudiante()

        response = self.client.get('/estudiantes/inicio/historial-clinico/')

        self.assertContains(response, 'Gripe con fiebre')
        self.assertContains(response, 'Notificado al tutor')

    def test_director_edita_historial(self):
        self._crear_historial()
        self._login_director()

        response = self.client.post(
            f'/estudiantes/historial-clinico/{self.estudiante.pk}/editar/',
            {
                'grupo_sanguineo': 'AB+',
                'alergias': 'Maní',
                'condiciones_medicas': 'Ninguna',
                'medicamentos_habituales': 'Ninguno',
                'vacunas': '',
                'contacto_emergencia_nombre': 'Pedro Perez',
                'contacto_emergencia_telefono': '809-555-0188',
                'contacto_emergencia_parentesco': 'Padre',
                'contacto_emergencia_secundario_nombre': '',
                'contacto_emergencia_secundario_telefono': '',
                'observaciones': '',
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        historial = HistorialClinicoEstudiante.objects.get(
            estudiante=self.estudiante
        )
        self.assertEqual(historial.grupo_sanguineo, 'AB+')
        self.assertEqual(historial.alergias, 'Maní')

    def test_director_registra_atencion(self):
        self._crear_historial()
        self._login_director()

        response = self.client.post(
            f'/estudiantes/historial-clinico/{self.estudiante.pk}/registro/',
            {
                'tipo': 'accidente',
                'fecha': '2026-04-15',
                'descripcion': 'Caída en el recreo',
                'atencion_proporcionada': 'Curaciones',
                'medicamento': '',
                'notificado_a_tutor': 'on',
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        registro = RegistroSalud.objects.get(estudiante=self.estudiante)
        self.assertEqual(registro.tipo, 'accidente')
        self.assertTrue(registro.notificado_a_tutor)
        self.assertEqual(registro.registrado_por, self.director)

    def test_director_elimina_registro(self):
        self._crear_historial()
        registro = RegistroSalud.objects.create(
            estudiante=self.estudiante,
            tipo='atencion',
            fecha='2026-04-15',
            descripcion='Atención general',
            registrado_por=self.director,
        )
        self._login_director()

        response = self.client.post(
            f'/estudiantes/registro-salud/{registro.pk}/eliminar/',
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            RegistroSalud.objects.filter(pk=registro.pk).exists()
        )

    def test_director_no_accede_a_historial_de_otro_centro(self):
        otro_centro = CentroEducativo.objects.create(
            nombre='Colegio Ajeno',
            codigo_minerd='MIN-0999'
        )
        otro_usuario = Usuario.objects.create_user(
            username='esthc2',
            email='esthc2@test.com',
            password='clave123'
        )
        otro_usuario.rol = 'estudiante'
        otro_usuario.save()

        otro_estudiante = Estudiante.objects.create(
            usuario=otro_usuario,
            centro=otro_centro,
            matricula='20260021',
            primer_nombre='Luis',
            primer_apellido='Rojas',
            sexo='M',
            fecha_nacimiento='2010-11-01',
            lugar_nacimiento='La Vega',
            nacionalidad='Dominicana',
            direccion='Calle 21',
            nombre_tutor='Tutor',
            cedula_tutor='00100000021',
            telefono_tutor='809-555-0121',
            parentesco_tutor='Padre',
        )

        self._login_director()

        response = self.client.get(
            f'/estudiantes/historial-clinico/{otro_estudiante.pk}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            '/',
            fetch_redirect_response=False
        )

    def test_listado_filtra_por_grado(self):
        anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio='2026-01-05',
            fecha_fin='2026-06-30',
            activo=True,
        )
        nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria'
        )
        grado = Grado.objects.create(
            nivel=nivel,
            nombre='1ro',
            orden=1
        )
        seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='A'
        )
        grado.secciones.add(seccion)

        Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=anio,
            grado=grado,
            seccion=seccion,
        )

        self._login_director()

        response = self.client.get(
            f'/estudiantes/historial-clinico/?grado={grado.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())

    def test_secretaria_ve_boton_historial_en_detalle(self):
        self._login_estudiante()
        self.client.logout()

        usuario = Usuario.objects.create_user(
            username='sechc',
            email='sechc@test.com',
            password='clave123'
        )
        usuario.rol = 'secretaria'
        usuario.save()

        self.client.login(username='sechc', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        response = self.client.get(
            f'/estudiantes/{self.estudiante.pk}/'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'/estudiantes/historial-clinico/{self.estudiante.pk}/'
        )

    def test_director_ve_boton_historial_en_detalle(self):
        self._login_director()

        response = self.client.get(
            f'/estudiantes/{self.estudiante.pk}/'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'/estudiantes/historial-clinico/{self.estudiante.pk}/'
        )

    def test_rol_no_permitido_redirige_a_home(self):
        self.client.login(username='directorhc', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        response = self.client.get(
            '/estudiantes/inicio/historial-clinico/'
        )

        self.assertRedirects(response, '/', fetch_redirect_response=False)


class CacheEstudiantesTests(TestCase):

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            activo=True
        )

        nivel = Nivel.objects.create(centro=self.centro, nombre='Primaria')
        self.grado = Grado.objects.create(nivel=nivel, nombre='1ro')
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.grado.secciones.add(self.seccion)

        self.estudiante = Estudiante.objects.create(
            usuario=Usuario.objects.create_user(
                username='estcache',
                email='estcache@test.com',
                password='clave123'
            ),
            centro=self.centro,
            matricula='20260001',
            primer_nombre='Ana',
            primer_apellido='Perez',
            sexo='F',
            fecha_nacimiento='2010-05-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle Prueba',
            nombre_tutor='Tutor',
            cedula_tutor='00100000003',
            telefono_tutor='809-555-0103',
            parentesco_tutor='Madre',
        )

        self.observacion = ObservacionEstudiante.objects.create(
            estudiante=self.estudiante,
            anio_escolar=self.anio,
            tipo='amonestacion',
            fecha='2026-08-01',
            descripcion='Llegada tarde repetida.',
        )

    def test_observaciones_segunda_llamada_sin_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from estudiantes.services.listados import observaciones_del_centro

        primera = observaciones_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = observaciones_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nueva_observacion_invalida_lista(self):
        from estudiantes.services.listados import observaciones_del_centro

        antes = observaciones_del_centro(self.centro)
        self.assertEqual(len(antes), 1)

        ObservacionEstudiante.objects.create(
            estudiante=self.estudiante,
            anio_escolar=self.anio,
            tipo='merito',
            fecha='2026-08-02',
            descripcion='Reconocimiento.',
        )

        despues = observaciones_del_centro(self.centro)
        self.assertEqual(len(despues), 2)

    def test_constancias_segunda_llamada_sin_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from estudiantes.services.listados import estudiantes_del_centro

        Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )

        primera = estudiantes_del_centro(self.centro, self.anio)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = estudiantes_del_centro(self.centro, self.anio)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_solicitudes_segunda_llamada_sin_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from estudiantes.services.listados import solicitudes_del_centro

        SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.estudiante.usuario,
            tipo_certificado='constancia_estudio',
            metodo_pago='efectivo',
            monto=450,
        )

        primera = solicitudes_del_centro(self.centro)
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = solicitudes_del_centro(self.centro)
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nueva_solicitud_invalida_lista(self):
        from estudiantes.services.listados import solicitudes_del_centro

        antes = solicitudes_del_centro(self.centro)
        self.assertEqual(len(antes), 0)

        SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.estudiante.usuario,
            tipo_certificado='record_notas',
            metodo_pago='efectivo',
            monto=450,
        )

        despues = solicitudes_del_centro(self.centro)
        self.assertEqual(len(despues), 1)

    def test_constancias_vista_con_inscripcion_no_rompe(self):
        Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )

        director = Usuario.objects.create_user(
            username='dirconst',
            email='dirconst@test.com',
            password='clave123'
        )
        director.rol = 'director'
        director.save()

        self.client.login(username='dirconst', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        response = self.client.get('/estudiantes/constancias/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())
        self.assertContains(response, self.grado.nombre)

    def test_constancias_vista_sin_inscripcion_no_rompe(self):
        director = Usuario.objects.create_user(
            username='dirconst2',
            email='dirconst2@test.com',
            password='clave123'
        )
        director.rol = 'director'
        director.save()

        self.client.login(username='dirconst2', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        response = self.client.get('/estudiantes/constancias/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.nombre_completo())


class SolicitudCertificadoAdminTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_certificados=True,
            modulo_caja=True,
            precio_certificado=450,
            permitir_pago_online=True,
        )

        self.usuario_estudiante = Usuario.objects.create_user(
            username='estcert',
            email='estcert@test.com',
            password='clave123'
        )
        self.usuario_estudiante.rol = 'estudiante'
        self.usuario_estudiante.save()

        self.estudiante = Estudiante.objects.create(
            usuario=self.usuario_estudiante,
            centro=self.centro,
            matricula='20260002',
            primer_nombre='Luis',
            primer_apellido='Gomez',
            sexo='M',
            fecha_nacimiento='2011-01-15',
            lugar_nacimiento='Santiago',
            nacionalidad='Dominicana',
            direccion='Calle 2',
            nombre_tutor='Tutor',
            cedula_tutor='00100000004',
            telefono_tutor='809-555-0104',
            parentesco_tutor='Padre',
        )

        self.director = Usuario.objects.create_user(
            username='direccert',
            email='direccert@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

        self.solicitud = SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.usuario_estudiante,
            tipo_certificado='constancia_estudio',
            metodo_pago='efectivo',
            motivo='Para trabajo',
            monto=450,
        )

    def _login_director(self):
        self.client.login(username='direccert', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _login_estudiante(self):
        self.client.login(username='estcert', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_estudiante_no_accede_al_panel(self):
        self._login_estudiante()

        response = self.client.get('/estudiantes/solicitudes/')

        self.assertEqual(response.status_code, 403)

    def test_director_ve_listado(self):
        self._login_director()

        response = self.client.get('/estudiantes/solicitudes/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.solicitud.folio)
        self.assertContains(response, self.estudiante.nombre_completo())

    def test_aprobar(self):
        self._login_director()

        response = self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/aprobar/'
        )

        self.assertRedirects(
            response,
            '/estudiantes/solicitudes/',
            fetch_redirect_response=False,
        )

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'aprobada')
        self.assertEqual(self.solicitud.aprobado_por, self.director)
        self.assertIsNotNone(self.solicitud.aprobado_en)

    def test_rechazar_con_motivo(self):
        self._login_director()

        response = self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/rechazar/',
            {'rechazo_motivo': 'Datos incompletos'}
        )

        self.assertRedirects(
            response,
            '/estudiantes/solicitudes/',
            fetch_redirect_response=False,
        )

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'rechazada')
        self.assertEqual(self.solicitud.rechazo_motivo, 'Datos incompletos')

    def test_rechazar_sin_motivo_no_guarda(self):
        self._login_director()

        self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/rechazar/',
            {'rechazo_motivo': ''}
        )

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'pendiente')

    def test_cobrar_requiere_aprobada(self):
        self._login_director()

        self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/cobrar/',
            {'referencia_pago': ''}
        )

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'pendiente')
        self.assertFalse(self.solicitud.pagado)

    def test_flujo_completo_aprobar_cobrar_entregar(self):
        self._login_director()

        self.client.post(f'/estudiantes/solicitudes/{self.solicitud.pk}/aprobar/')
        self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/cobrar/',
            {'referencia_pago': 'REC-001'}
        )
        self.client.post(f'/estudiantes/solicitudes/{self.solicitud.pk}/entregar/')

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'entregada')
        self.assertTrue(self.solicitud.pagado)
        self.assertEqual(self.solicitud.referencia_pago, 'REC-001')
        self.assertEqual(self.solicitud.entregado_por, self.director)
        self.assertIsNotNone(self.solicitud.pagado_en)
        self.assertIsNotNone(self.solicitud.entregado_en)

    def test_anular_pago_online_reembolsa(self):
        solicitud_online = SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.usuario_estudiante,
            tipo_certificado='constancia_conducta',
            metodo_pago='online',
            monto=450,
        )

        from estudiantes.services.pagos import procesar_pago_online

        referencia, error = procesar_pago_online(solicitud_online)
        self.assertIsNone(error)

        solicitud_online.refresh_from_db()
        self.assertEqual(solicitud_online.estado, 'pagada')
        self.assertTrue(solicitud_online.pagado)

        self._login_director()

        self.client.post(
            f'/estudiantes/solicitudes/{solicitud_online.pk}/anular/'
        )

        solicitud_online.refresh_from_db()
        self.assertEqual(solicitud_online.estado, 'anulada')
        self.assertFalse(solicitud_online.pagado)
        self.assertEqual(solicitud_online.referencia_pago, '')

    def test_no_anular_entregada(self):
        self.solicitud.estado = 'entregada'
        self.solicitud.pagado = True
        self.solicitud.save()

        self._login_director()

        self.client.post(
            f'/estudiantes/solicitudes/{self.solicitud.pk}/anular/'
        )

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'entregada')


class DeudaBloqueaCertificadosTests(TestCase):

    HOY = date(2026, 8, 15)

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0004'
        )

        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro,
            modulo_certificados=True,
            modulo_caja=True,
            precio_certificado=450,
        )

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.usuario_estudiante = Usuario.objects.create_user(
            username='estdeuda',
            email='estdeuda@test.com',
            password='clave123'
        )
        self.usuario_estudiante.rol = 'estudiante'
        self.usuario_estudiante.save()

        self.estudiante = Estudiante.objects.create(
            usuario=self.usuario_estudiante,
            centro=self.centro,
            matricula='20261001',
            primer_nombre='Carlos',
            primer_apellido='Díaz',
            sexo='M',
            fecha_nacimiento='2011-02-20',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 4',
            nombre_tutor='Tutor',
            cedula_tutor='00100000005',
            telefono_tutor='809-555-0105',
            parentesco_tutor='Padre',
        )

        self.director = Usuario.objects.create_user(
            username='dircdeuda',
            email='dircdeuda@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

        self.concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
            es_recurrente=True,
        )

    def _login_director(self):
        self.client.login(username='dircdeuda', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _login_estudiante(self):
        self.client.login(username='estdeuda', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _asignar_con_deuda(self):
        AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )

    def _asignar_pagada(self):
        asignacion = AsignacionConcepto.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            anio_escolar=self.anio,
            activo=True,
        )
        from caja.models import Pago

        Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('15000.00'),
            recibo=1,
            fecha=self.HOY,
            creado_por=self.director,
        )
        return asignacion

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_constancia_con_deuda_se_bloquea(self, _hoy):
        self._asignar_con_deuda()
        self._login_director()

        response = self.client.get(
            f'/estudiantes/constancia/{self.estudiante.id}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            '/estudiantes/constancias/',
            fetch_redirect_response=False,
        )

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_constancia_sin_deuda_se_imprime(self, _hoy):
        self._asignar_pagada()
        self._login_director()

        response = self.client.get(
            f'/estudiantes/constancia/{self.estudiante.id}/'
        )

        self.assertEqual(response.status_code, 200)

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_listado_muestra_badge_de_deuda(self, _hoy):
        self._asignar_con_deuda()
        self._login_director()

        response = self.client.get('/estudiantes/constancias/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vencida')

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_solicitud_estudiante_con_deuda_se_bloquea(self, _hoy):
        self._asignar_con_deuda()
        self._login_estudiante()

        response = self.client.post(
            '/estudiantes/inicio/solicitudes/',
            {
                'tipo_certificado': 'constancia_estudio',
                'metodo_pago': 'efectivo',
                'motivo': 'Para trabajo',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'No puedes solicitar certificados mientras tengas deuda pendiente',
        )
        self.assertFalse(
            SolicitudCertificado.objects.filter(
                estudiante=self.estudiante
            ).exists()
        )

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_solicitud_estudiante_sin_deuda_se_registra(self, _hoy):
        self._asignar_pagada()
        self._login_estudiante()

        response = self.client.post(
            '/estudiantes/inicio/solicitudes/',
            {
                'tipo_certificado': 'constancia_estudio',
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

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_aprobar_con_deuda_se_bloquea(self, _hoy):
        self._asignar_con_deuda()
        self._login_director()

        solicitud = SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.usuario_estudiante,
            tipo_certificado='constancia_estudio',
            metodo_pago='efectivo',
            motivo='Para trabajo',
            monto=450,
        )

        response = self.client.post(
            f'/estudiantes/solicitudes/{solicitud.pk}/aprobar/',
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tiene deuda pendiente')
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')

    @patch('django.utils.timezone.localdate', return_value=HOY)
    def test_aprobar_sin_deuda_aprueba(self, _hoy):
        self._asignar_pagada()
        self._login_director()

        solicitud = SolicitudCertificado.objects.create(
            estudiante=self.estudiante,
            solicitante=self.usuario_estudiante,
            tipo_certificado='constancia_estudio',
            metodo_pago='efectivo',
            motivo='Para trabajo',
            monto=450,
        )

        response = self.client.post(
            f'/estudiantes/solicitudes/{solicitud.pk}/aprobar/',
        )

        self.assertRedirects(
            response,
            '/estudiantes/solicitudes/',
            fetch_redirect_response=False,
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')


class EstudianteCreateTutoresTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0004'
        )

        self.director = Usuario.objects.create_user(
            username='directorcrea',
            email='directorcrea@test.com',
            password='clave123'
        )
        self.director.rol = 'director'
        self.director.save()

        self.tutor = Tutor.objects.create(
            centro=self.centro,
            primer_nombre='Juan',
            primer_apellido='Gomez',
            cedula='00100000004',
            sexo='M',
            fecha_nacimiento='1980-04-03',
            nacionalidad='República Dominicana',
            direccion='Calle 4',
            telefono='8095550104',
        )

        self.client.login(username='directorcrea', password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _datos(self, tutor_id):
        return {
            'primer_nombre': 'Maria',
            'primer_apellido': 'Gomez',
            'sexo': 'F',
            'fecha_nacimiento': '2012-04-03',
            'lugar_nacimiento': 'Santo Domingo',
            'nacionalidad': 'República Dominicana',
            'direccion': 'Calle 1',
            'nombre_tutor': 'Juan Gomez',
            'cedula_tutor': '00100000003',
            'telefono_tutor': '8095550103',
            'parentesco_tutor': 'padre',
            'tutores': [str(tutor_id)],
        }

    def test_creacion_guarda_tutores_seleccionados(self):
        response = self.client.post(
            '/estudiantes/nuevo/',
            self._datos(self.tutor.pk),
        )

        self.assertEqual(response.status_code, 200)
        estudiante = Estudiante.objects.get(primer_nombre='Maria')
        self.assertEqual(list(estudiante.tutores.all()), [self.tutor])

    def test_creacion_sin_tutores_no_falla(self):
        datos = self._datos('')
        datos['tutores'] = []

        response = self.client.post(
            '/estudiantes/nuevo/',
            datos,
        )

        self.assertEqual(response.status_code, 200)
        estudiante = Estudiante.objects.get(primer_nombre='Maria')
        self.assertEqual(list(estudiante.tutores.all()), [])
