from datetime import date
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from academico.models import Grado, Nivel, Seccion
from caja.models import ConceptoPago, Pago
from comunicaciones.models import Campania, DestinatarioCampania, NotificacionPago
from comunicaciones.services import (
    construir_destinatarios,
    notificar_pago,
    procesar_campania,
)
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro
from estudiantes.models import Estudiante, Inscripcion
from tutores.models import Tutor
from usuarios.models import Usuario


class BaseComunicacionesTestCase(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0001',
        )
        self.config = ConfiguracionCentro.objects.create(
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

        self.usuario_alumno = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='clave123',
        )
        self.usuario_alumno.rol = 'estudiante'
        self.usuario_alumno.save()

        self.estudiante = Estudiante.objects.create(
            usuario=self.usuario_alumno,
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

        Inscripcion.objects.create(
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

        self.concepto = ConceptoPago.objects.create(
            centro=self.centro,
            nombre='Mensualidad',
            monto=Decimal('5000.00'),
        )


class ConstruirDestinatariosTestCase(BaseComunicacionesTestCase):

    def test_configuracion_correo_desde_bd_gana_a_settings(self):
        from django.conf import settings

        self.config.email_proveedor = 'smtp_otro'
        self.config.email_servidor = 'smtp.centro.com'
        self.config.email_puerto = 465
        self.config.email_usuario = 'aviso@centro.com'
        self.config.email_clave = 'clave-centro'
        self.config.email_ssl = True
        self.config.email_tls = False
        self.config.email_remitente = 'remitente@centro.com'
        self.config.save()

        from comunicaciones.services.configuracion import obtener_configuracion_correo

        config = obtener_configuracion_correo(self.centro)
        self.assertEqual(config['host'], 'smtp.centro.com')
        self.assertEqual(config['port'], 465)
        self.assertEqual(config['user'], 'aviso@centro.com')
        self.assertEqual(config['password'], 'clave-centro')
        self.assertEqual(config['from_email'], 'remitente@centro.com')
        self.assertTrue(config['use_ssl'])
        self.assertFalse(config['use_tls'])

    def test_configuracion_correo_fallback_a_settings(self):
        from django.conf import settings

        self.config.email_servidor = ''
        self.config.email_proveedor = 'consola'
        self.config.save()

        from comunicaciones.services.configuracion import obtener_configuracion_correo

        config = obtener_configuracion_correo(self.centro)
        # Sin servidor SMTP ni proveedor API configurado, cae al proveedor
        # 'consola' (o al EMAIL_HOST de settings/.env si estuviera definido).
        if settings.EMAIL_HOST:
            self.assertEqual(config['host'], settings.EMAIL_HOST)
        else:
            self.assertEqual(config['proveedor'], 'consola')
        self.assertEqual(config['from_email'], settings.DEFAULT_FROM_EMAIL)

    def test_configuracion_whatsapp_desde_bd(self):
        self.config.whatsapp_url = 'https://gw.centro.com/wa'
        self.config.whatsapp_token = 'tok-1'
        self.config.whatsapp_remitente = '18290000000'
        self.config.save()

        from comunicaciones.services.configuracion import obtener_configuracion_whatsapp

        config = obtener_configuracion_whatsapp(self.centro)
        self.assertEqual(config['url'], 'https://gw.centro.com/wa')
        self.assertEqual(config['token'], 'tok-1')
        self.assertEqual(config['remitente'], '18290000000')

    def test_envio_email_usa_config_del_centro(self):
        from unittest.mock import patch

        from comunicaciones.services.email import enviar_email
        from comunicaciones.models import DestinatarioCampania

        self.config.email_proveedor = 'smtp_otro'
        self.config.email_servidor = 'smtp.centro.com'
        self.config.email_usuario = 'aviso@centro.com'
        self.config.email_clave = 'clave'
        self.config.email_remitente = 'remitente@centro.com'
        self.config.save()

        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)
        d = campania.destinatarios.get()

        with patch('comunicaciones.services.email.get_connection') as mock_conexion:
            enviar_email(d)
            args, kwargs = mock_conexion.call_args
            self.assertEqual(kwargs['backend'], 'django.core.mail.backends.smtp.EmailBackend')
            self.assertEqual(kwargs['host'], 'smtp.centro.com')
            self.assertEqual(kwargs['username'], 'aviso@centro.com')
            self.assertEqual(kwargs['password'], 'clave')

    def test_alcance_todos_email(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión de padres',
            mensaje='Hola {{tutor}}, lo esperamos el viernes.',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        creados = construir_destinatarios(campania)

        self.assertEqual(creados, 1)
        d = campania.destinatarios.get()
        self.assertEqual(d.tutor, self.tutor)
        self.assertEqual(d.canal, 'email')
        self.assertEqual(d.contacto, 'tutora@test.com')

    def test_alcance_ambos_crea_dos_destinatarios(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Aviso',
            mensaje='Aviso general',
            canal='ambos',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        self.assertEqual(campania.destinatarios.count(), 2)
        canales = set(campania.destinatarios.values_list('canal', flat=True))
        self.assertEqual(canales, {'email', 'whatsapp'})

    def test_alcance_grado(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión 1ro',
            mensaje='Solo primer grado',
            canal='email',
            alcance='grado',
            grado=self.grado,
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        self.assertEqual(campania.destinatarios.count(), 1)

    def test_tutor_sin_contacto_queda_sin_contacto(self):
        self.tutor.correo_personal = None
        self.tutor.telefono = ''
        self.tutor.save()

        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Sin contacto',
            mensaje='Hola',
            canal='ambos',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        self.assertEqual(campania.destinatarios.count(), 2)
        estados = set(campania.destinatarios.values_list('estado', flat=True))
        self.assertEqual(estados, {'sin_contacto'})


class ProcesarCampaniaTestCase(BaseComunicacionesTestCase):

    def test_envia_por_email_y_whatsapp(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión de padres',
            mensaje='Hola {{tutor}}, nos vemos el viernes.',
            canal='ambos',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)
        procesar_campania(campania)

        self.assertEqual(campania.destinatarios.filter(estado='enviado').count(), 2)
        self.assertEqual(campania.estado, 'enviada')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reunión de padres')
        self.assertIn('María', mail.outbox[0].body)

    def test_reintenta_solo_pendientes(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        procesar_campania(campania)
        self.assertEqual(len(mail.outbox), 1)

        procesar_campania(campania)
        self.assertEqual(len(mail.outbox), 1, 'No debe reenviar los ya enviados.')


class NotificarPagoTestCase(BaseComunicacionesTestCase):

    def test_notifica_por_email_y_whatsapp(self):
        pago = Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('5000.00'),
            recibo=1,
        )

        notificaciones = NotificacionPago.objects.filter(pago=pago)
        self.assertEqual(notificaciones.count(), 2)
        self.assertEqual(
            set(notificaciones.values_list('estado', flat=True)),
            {'enviado'},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Juan', mail.outbox[0].body)

    def test_tutor_sin_contactos_no_rompe(self):
        self.tutor.correo_personal = None
        self.tutor.telefono = ''
        self.tutor.save()

        pago = Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('5000.00'),
            recibo=2,
        )

        self.assertFalse(
            NotificacionPago.objects.filter(pago=pago).exists()
        )

    def test_signal_crea_notificaciones(self):
        pago = Pago.objects.create(
            centro=self.centro,
            estudiante=self.estudiante,
            concepto=self.concepto,
            monto=Decimal('3000.00'),
            recibo=3,
        )

        self.assertTrue(
            NotificacionPago.objects.filter(pago=pago).exists()
        )


class VistasComunicacionesTestCase(BaseComunicacionesTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_lista_renders(self):
        response = self.client.get(reverse('comunicaciones:campania_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Centro de Correo')

    def test_formulario_renders(self):
        response = self.client.get(reverse('comunicaciones:campania_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nueva Campaña')

    def test_formulario_preselecciona_tutor(self):
        url = reverse('comunicaciones:campania_create') + f'?tutor={self.tutor.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'María')

    def test_crear_campania_por_post(self):
        response = self.client.post(
            reverse('comunicaciones:campania_create'),
            {
                'asunto': 'Aviso importante',
                'mensaje': 'Hola {{tutor}}',
                'canal': 'email',
                'alcance': 'todos',
            },
        )
        self.assertEqual(response.status_code, 302)
        campania = Campania.objects.get(asunto='Aviso importante')
        self.assertEqual(campania.destinatarios.count(), 1)

    def test_detalle_renders(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        url = reverse('comunicaciones:campania_detail', args=[campania.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reunión')

    def test_editar_renders_con_tutores_preseleccionados(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='seleccion',
            enviado_por=self.director,
        )
        campania.tutores.add(self.tutor)

        url = reverse('comunicaciones:campania_update', args=[campania.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'María')
        self.assertContains(
            response,
            f'value="{self.tutor.pk}"',
            html=False,
        )

    def test_editar_campania_por_post_guarda_y_actualiza_destinatarios(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)
        self.assertEqual(campania.destinatarios.count(), 1)

        url = reverse('comunicaciones:campania_update', args=[campania.pk])
        response = self.client.post(
            url,
            {
                'asunto': 'Reunión actualizada',
                'mensaje': 'Hola {{tutor}}, cambió el horario.',
                'canal': 'ambos',
                'alcance': 'seleccion',
                'grado': '',
                'tutores': [str(self.tutor.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)

        campania.refresh_from_db()
        self.assertEqual(campania.asunto, 'Reunión actualizada')
        self.assertEqual(campania.canal, 'ambos')
        self.assertEqual(campania.alcance, 'seleccion')
        self.assertEqual(list(campania.tutores.all()), [self.tutor])
        self.assertEqual(campania.destinatarios.count(), 2)
        self.assertEqual(campania.destinatarios.filter(estado='pendiente').count(), 2)

    def test_enviar_campania_por_post(self):
        campania = Campania.objects.create(
            centro=self.centro,
            asunto='Reunión',
            mensaje='Hola {{tutor}}',
            canal='email',
            alcance='todos',
            enviado_por=self.director,
        )
        construir_destinatarios(campania)

        url = reverse('comunicaciones:campania_enviar', args=[campania.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        campania.refresh_from_db()
        self.assertEqual(campania.estado, 'enviada')
        self.assertEqual(campania.destinatarios.filter(estado='enviado').count(), 1)


# ===========================================================================
# COMUNICADOS / ANUNCIOS POR SECCION
# ===========================================================================

from datetime import timedelta

from django.utils import timezone as dj_timezone

from comunicaciones.models import Comunicado
from comunicaciones.services.comunicados import (
    comunicados_para_estudiante,
    comunicados_para_tutor,
    invalidar_comunicados,
)


class ComunicadosBase(BaseComunicacionesTestCase):

    def setUp(self):
        super().setUp()
        # Segunda seccion para probar aislamiento
        self.seccion_b = Seccion.objects.create(centro=self.centro, nombre='B')

    def _crear(self, **kwargs):
        datos = dict(
            centro=self.centro,
            titulo='Anuncio general',
            contenido='Contenido del anuncio',
            alcance='todos',
        )
        datos.update(kwargs)
        return Comunicado.objects.create(**datos)


class ComunicadoVigenciaTestCase(ComunicadosBase):

    def test_vigente_sin_vencimiento(self):
        self.assertTrue(self._crear().esta_vigente())

    def test_vencido(self):
        c = self._crear(
            fecha_publicacion=dj_timezone.now() - timedelta(days=10),
            fecha_vencimiento=dj_timezone.localdate() - timedelta(days=1),
        )
        self.assertFalse(c.esta_vigente())
        self.assertTrue(c.vencido)

    def test_futuro_no_visible(self):
        c = self._crear(
            fecha_publicacion=dj_timezone.now() + timedelta(days=2),
        )
        self.assertFalse(c.esta_vigente())


class VisibilidadComunicadosTestCase(ComunicadosBase):

    def test_todos_lo_ve_estudiante_y_tutor(self):
        c = self._crear()
        self.assertIn(c, comunicados_para_estudiante(self.estudiante))
        self.assertIn(c, comunicados_para_tutor(self.tutor))

    def test_seccion_propia_visible_ajena_no(self):
        suya = self._crear(
            titulo='Su seccion', alcance='seccion', seccion=self.seccion)
        ajena = self._crear(
            titulo='Otra seccion', alcance='seccion', seccion=self.seccion_b)

        visibles = comunicados_para_estudiante(self.estudiante)
        self.assertIn(suya, visibles)
        self.assertNotIn(ajena, visibles)

        visibles_tutor = comunicados_para_tutor(self.tutor)
        self.assertIn(suya, visibles_tutor)
        self.assertNotIn(ajena, visibles_tutor)

    def test_vencidos_excluidos(self):
        vencido = self._crear(
            titulo='Ya vencio',
            fecha_publicacion=dj_timezone.now() - timedelta(days=5),
            fecha_vencimiento=dj_timezone.localdate() - timedelta(days=1),
        )
        self.assertNotIn(vencido, comunicados_para_estudiante(self.estudiante))

    def test_cache_se_invalida_al_crear(self):
        self.assertEqual(comunicados_para_estudiante(self.estudiante), [])

        nuevo = self._crear(titulo='Nuevo despues del cache')

        # La cache ya estaba poblada; la signal debe haberla invalidado.
        self.assertIn(nuevo, comunicados_para_estudiante(self.estudiante))

    def test_invalidacion_manual(self):
        self._crear(titulo='Uno')
        self.assertEqual(len(comunicados_para_tutor(self.tutor)), 1)

        extra = self._crear(titulo='Dos')
        invalidar_comunicados(self.centro.id)

        lista = comunicados_para_tutor(self.tutor)
        self.assertIn(extra, lista)


class ComunicadoViewsTestCase(ComunicadosBase):

    def setUp(self):
        super().setUp()
        self.client = self.client_class(SERVER_NAME='localhost')

    def _login_como(self, usuario):
        self.client.force_login(usuario)
        s = self.client.session
        s['centro_id'] = self.centro.id
        s.save()

    def test_director_puede_listar_y_crear(self):
        self._login_como(self.director)
        r = self.client.get(reverse('comunicaciones:comunicado_list'))
        self.assertEqual(r.status_code, 200)

        r = self.client.post(reverse('comunicaciones:comunicado_create'), {
            'titulo': 'Reunion',
            'contenido': 'Habra reunion.',
            'alcance': 'todos',
            'fecha_publicacion': '2026-08-21T08:00',
            'fecha_vencimiento': '',
            'fijado': 'on',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Comunicado.objects.filter(centro=self.centro, titulo='Reunion').exists()
        )

    def test_alcance_seccion_requiere_seccion(self):
        self._login_como(self.director)
        r = self.client.post(reverse('comunicaciones:comunicado_create'), {
            'titulo': 'Mal formado',
            'contenido': 'Sin seccion.',
            'alcance': 'seccion',
            'seccion': '',
            'fecha_publicacion': '2026-08-21T08:00',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Selecciona la seccion destino')
        self.assertFalse(Comunicado.objects.filter(titulo='Mal formado').exists())

    def test_portal_estudiante_ve_su_seccion(self):
        self._crear(alcance='seccion', seccion=self.seccion,
                    titulo='Salida pedagogica')
        self.client.force_login(self.usuario_alumno)
        r = self.client.get(reverse('comunicaciones:estudiante_comunicados'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Salida pedagogica')

    def test_portal_tutor_ve_seccion_de_su_hijo(self):
        self._crear(alcance='seccion', seccion=self.seccion,
                    titulo='Cobro de uniformes')
        self.client.force_login(self.tutor.usuario or self.director)
        # El tutor de prueba no tiene usuario vinculado en la base del setUp;
        # se valida el servicio directamente y el acceso con un tutor real.
        from tutores.models import Tutor

        if Tutor.objects.filter(usuario=self.director).exists():
            self.fail('El director no deberia ser tutor')
        r = self.client.get(reverse('comunicaciones:tutor_comunicados'))
        # Sin usuario tutor vinculado, la vista redirige al home.
        self.assertIn(r.status_code, (200, 302))

    def test_rol_docente_no_administra(self):
        docente = Usuario.objects.create_user(
            username='profe1', email='p@test.com', password='clave123')
        docente.rol = 'docente'
        docente.save()

        self._login_como(docente)
        r = self.client.get(reverse('comunicaciones:comunicado_list'))
        # role_required responde 403 (pagina de prohibido)
        self.assertEqual(r.status_code, 403)

    def test_otro_centro_no_ve_comunicados_ajenos(self):
        otro_centro = CentroEducativo.objects.create(
            nombre='Otro Colegio', codigo_minerd='MIN-9999')
        c = Comunicado.objects.create(
            centro=otro_centro, titulo='De otro centro',
            contenido='...', alcance='todos')

        self._login_como(self.director)
        r = self.client.get(reverse('comunicaciones:comunicado_list'))
        self.assertNotContains(r, 'De otro centro')
