from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.template import Context
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.middleware import PermisoPaginaMiddleware
from core.models import CentroEducativo, ConfiguracionCentro, PermisoPagina, RolCentro
from core.services import centros_listado
from core.templatetags.permisos import has_perm_page
from usuarios.models import Usuario


class CacheCentrosListadoTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Alfa',
            codigo_minerd='MIN-C1'
        )

    def test_segunda_llamada_sin_consultas(self):
        primera = centros_listado()
        self.assertEqual(len(primera), 1)

        with CaptureQueriesContext(connection) as ctx:
            segunda = centros_listado()
        self.assertEqual(len(ctx), 0)
        self.assertEqual(len(segunda), 1)

    def test_nuevo_centro_invalida_listado(self):
        antes = centros_listado()
        self.assertEqual(len(antes), 1)

        CentroEducativo.objects.create(
            nombre='Colegio Beta',
            codigo_minerd='MIN-C2'
        )

        despues = centros_listado()
        self.assertEqual(len(despues), 2)

    def test_borrar_centro_invalida_listado(self):
        antes = centros_listado()
        self.assertEqual(len(antes), 1)

        self.centro.delete()

        despues = centros_listado()
        self.assertEqual(len(despues), 0)


class ConfiguracionCorreoCentralTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Prueba',
            codigo_minerd='MIN-CC1',
        )
        self.director = Usuario.objects.create_user(
            username='director_cfg',
            email='director@prueba.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

    def _login(self):
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_formulario_incluye_campos_de_correo(self):
        self._login()
        ConfiguracionCentro.objects.create(centro=self.centro)
        response = self.client.get(reverse('core:configuracion_centro'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email_servidor')
        self.assertContains(response, 'whatsapp_url')

    def test_guardar_configuracion_correo(self):
        self._login()
        config = ConfiguracionCentro.objects.create(centro=self.centro)

        response = self.client.post(
            reverse('core:configuracion_centro'),
            {
                'usa_calificacion_numerica': 'on',
                'nota_minima_aprobacion': '70.00',
                'usa_competencias': 'on',
                'permite_completivo': 'on',
                'tipo_pago_nomina': 'mensual',
                'modulo_asistencia': 'on',
                'modulo_caja': 'on',
                'modulo_mensajeria': 'on',
                'modulo_reportes': 'on',
                'precio_certificado': '0.00',
                'email_servidor': 'smtp.gmail.com',
                'email_puerto': '587',
                'email_usuario': 'correo@prueba.com',
                'email_clave': 'clave-secreta',
                'email_tls': 'on',
                'email_remitente': 'notificaciones@prueba.com',
                'whatsapp_url': 'https://gw.prueba.com/wa',
                'whatsapp_token': 'token-123',
            },
        )
        self.assertEqual(response.status_code, 302)

        config.refresh_from_db()
        self.assertEqual(config.email_servidor, 'smtp.gmail.com')
        self.assertEqual(config.email_usuario, 'correo@prueba.com')
        self.assertEqual(config.email_clave, 'clave-secreta')
        self.assertEqual(config.whatsapp_url, 'https://gw.prueba.com/wa')
        self.assertTrue(config.email_tls)

    def test_correo_de_prueba_enviado(self):
        self._login()
        response = self.client.post(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['director@prueba.com'])
        self.assertIn('prueba', mail.outbox[0].body)

    def test_correo_de_prueba_sin_email_de_usuario(self):
        self.director.email = ''
        self.director.save()
        self._login()

        response = self.client.post(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_de_prueba_solo_por_post(self):
        self._login()
        response = self.client.get(reverse('core:test_correo'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


def _crear_usuario(username, rol=None, superusuario=False):
    usuario = Usuario.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='clave123',
    )
    if superusuario:
        usuario.is_staff = True
        usuario.is_superuser = True
    usuario.rol = rol or 'superadmin'
    usuario.save()
    return usuario


class HasPermPageTagTests(TestCase):

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.rol_director, _ = RolCentro.objects.get_or_create(nombre='director')
        self.rol_docente, _ = RolCentro.objects.get_or_create(nombre='docente')
        self.permiso = PermisoPagina.objects.create(url_name='estudiante_list')
        self.permiso.roles_permitidos.add(self.rol_director)

    def _evaluar(self, usuario):
        request = self.factory.get('/estudiantes/')
        request.user = usuario
        return has_perm_page(Context({'request': request}), 'estudiante_list')

    def test_superusuario_siempre_pasa(self):
        self.assertTrue(self._evaluar(_crear_usuario('super1', superusuario=True)))

    def test_sin_registro_pagina_abierta(self):
        PermisoPagina.objects.all().delete()
        cache.clear()
        usuario = _crear_usuario('cajero1', rol='cajero')
        self.assertTrue(self._evaluar(usuario))

    def test_rol_permitido_pasa(self):
        usuario = _crear_usuario('director1', rol='director')
        self.assertTrue(self._evaluar(usuario))

    def test_ajeno_denegado_y_usuario_directo_permitido(self):
        usuario = _crear_usuario('docente1', rol='docente')
        self.assertFalse(self._evaluar(usuario))

        self.permiso.usuarios_permitidos.add(usuario)
        cache.clear()
        self.assertTrue(self._evaluar(usuario))

    def test_memoizacion_por_request(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        usuario = _crear_usuario('director2', rol='director')
        request = self.factory.get('/estudiantes/')
        request.user = usuario
        contexto = Context({'request': request})

        has_perm_page(contexto, 'estudiante_list')
        with CaptureQueriesContext(connection) as ctx:
            for _ in range(5):
                has_perm_page(contexto, 'estudiante_list')
        self.assertEqual(len(ctx), 0)


class PermisoPaginaMiddlewareTests(TestCase):

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.rol_director, _ = RolCentro.objects.get_or_create(nombre='director')

    def _procesar(self, usuario, path='/centros/'):
        request = self.factory.get(path)
        request.user = usuario
        respuesta_dummy = lambda req: 'OK'
        middleware = PermisoPaginaMiddleware(respuesta_dummy)
        return middleware(request)

    def test_anonimo_pasa(self):
        respuesta = self._procesar(AnonymousUser())
        self.assertEqual(respuesta, 'OK')

    def test_superusuario_pasa_con_restriccion(self):
        _crear_usuario('supermw', superusuario=True)
        permiso = PermisoPagina.objects.create(url_name='core:centro_list')
        permiso.roles_permitidos.add(self.rol_director)
        cache.clear()

        superusuario = Usuario.objects.filter(username='supermw').first()
        respuesta = self._procesar(superusuario)
        self.assertEqual(respuesta, 'OK')

    def test_rol_permitido_pasa(self):
        permiso = PermisoPagina.objects.create(url_name='core:centro_list')
        permiso.roles_permitidos.add(self.rol_director)

        director = _crear_usuario('directormw', rol='director')
        self.assertEqual(self._procesar(director), 'OK')

    def test_ajeno_recibe_403(self):
        permiso = PermisoPagina.objects.create(url_name='core:centro_list')
        permiso.roles_permitidos.add(self.rol_director)

        docente = _crear_usuario('docentemw', rol='docente')
        respuesta = self._procesar(docente)
        self.assertEqual(respuesta.status_code, 403)


class PermisoPaginaVistasTests(TestCase):

    def setUp(self):
        cache.clear()
        self.superadmin = _crear_usuario('root', superusuario=True)
        self.secretaria = _crear_usuario('secv', rol='secretaria')
        self.rol_director, _ = RolCentro.objects.get_or_create(nombre='director')

    def test_listado_requiere_superadmin(self):
        self.client.force_login(self.secretaria)
        respuesta = self.client.get(reverse('core:permiso_pagina_list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_superadmin_ve_listado(self):
        self.client.force_login(self.superadmin)
        respuesta = self.client.get(reverse('core:permiso_pagina_list'))
        self.assertEqual(respuesta.status_code, 200)

    def test_crear_limpia_cache(self):
        cache.set('perm_mw:nomina:dashboard', 'viejo', 300)
        cache.set('perm_page:nomina:dashboard', 'viejo', 300)

        self.client.force_login(self.superadmin)
        rol = RolCentro.objects.get(nombre='director')
        respuesta = self.client.post(reverse('core:permiso_pagina_create'), {
            'url_name': 'nomina:dashboard',
            'descripcion': 'Panel de nómina',
            'roles_permitidos': [rol.pk],
            'usuarios_permitidos': [],
            'activo': 'on',
        })
        self.assertRedirects(respuesta, reverse('core:permiso_pagina_list'))
        self.assertTrue(PermisoPagina.objects.filter(url_name='nomina:dashboard').exists())
        self.assertIsNone(cache.get('perm_mw:nomina:dashboard'))
        self.assertIsNone(cache.get('perm_page:nomina:dashboard'))

    def test_editar_url_invalida_cache_vieja_y_nueva(self):
        permiso = PermisoPagina.objects.create(
            url_name='viejo:url', descripcion='temporal'
        )
        cache.set('perm_mw:viejo:url', 'x', 300)

        self.client.force_login(self.superadmin)
        respuesta = self.client.post(
            reverse('core:permiso_pagina_update', args=[permiso.pk]),
            {
                'url_name': 'nuevo:url',
                'descripcion': 'actualizado',
                'roles_permitidos': [],
                'usuarios_permitidos': [],
                'activo': 'on',
            },
        )
        self.assertRedirects(respuesta, reverse('core:permiso_pagina_list'))
        self.assertIsNone(cache.get('perm_mw:viejo:url'))
        permiso.refresh_from_db()
        self.assertEqual(permiso.url_name, 'nuevo:url')

    def test_eliminar_permiso_abre_la_pagina(self):
        permiso = PermisoPagina.objects.create(url_name='auditoria:bitacora')
        self.client.force_login(self.superadmin)
        respuesta = self.client.post(
            reverse('core:permiso_pagina_delete', args=[permiso.pk])
        )
        self.assertRedirects(respuesta, reverse('core:permiso_pagina_list'))
        self.assertFalse(PermisoPagina.objects.filter(pk=permiso.pk).exists())


class SeedPermisosTests(TestCase):

    def test_crea_roles_y_permisos_por_defecto(self):
        call_command('seed_permisos', verbosity=0)

        for nombre in ('superadmin', 'admin', 'director', 'secretaria', 'tutor'):
            self.assertTrue(RolCentro.objects.filter(nombre=nombre).exists())

        permiso = PermisoPagina.objects.get(url_name='estudiante_list')
        nombres = set(permiso.roles_permitidos.values_list('nombre', flat=True))
        self.assertEqual(nombres, {'director', 'secretaria', 'admin', 'superadmin'})

    def test_idempotente(self):
        call_command('seed_permisos', verbosity=0)
        total_antes = PermisoPagina.objects.count()
        roles_antes = list(
            PermisoPagina.objects.get(
                url_name='estudiante_list'
            ).roles_permitidos.values_list('nombre', flat=True)
        )

        call_command('seed_permisos', verbosity=0)

        self.assertEqual(PermisoPagina.objects.count(), total_antes)
        self.assertEqual(
            list(
                PermisoPagina.objects.get(
                    url_name='estudiante_list'
                ).roles_permitidos.values_list('nombre', flat=True)
            ),
            roles_antes,
        )

    def test_solo_faltantes_no_pisa_cambios(self):
        call_command('seed_permisos', verbosity=0)

        permiso = PermisoPagina.objects.get(url_name='docente_list')
        permiso.roles_permitidos.clear()
        cache.clear()

        call_command('seed_permisos', solo_faltantes=True, verbosity=0)

        permiso.refresh_from_db()
        self.assertEqual(permiso.roles_permitidos.count(), 0)


class PermisoM2MInvalidaCacheTests(TestCase):

    def setUp(self):
        cache.clear()
        self.rol_director, _ = RolCentro.objects.get_or_create(nombre='director')
        self.rol_docente, _ = RolCentro.objects.get_or_create(nombre='docente')
        self.permiso = PermisoPagina.objects.create(url_name='disciplina')
        self.permiso.roles_permitidos.add(self.rol_director)

    def test_cambio_de_roles_invalida_cache(self):
        cache.set('perm_mw:disciplina', 'stale', 300)
        cache.set('perm_page:disciplina', 'stale', 300)

        self.permiso.roles_permitidos.set([self.rol_docente])

        self.assertIsNone(cache.get('perm_mw:disciplina'))
        self.assertIsNone(cache.get('perm_page:disciplina'))
