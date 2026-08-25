"""Pruebas de la validación de notas pendientes al cerrar períodos
(Gap 1 del análisis de cierre) y del bloqueo por completivo sin
procesar al cerrar el año (Gap 2).
"""

from datetime import date

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academico.models import (
    AreaCurricular,
    Asignatura,
    Calificacion,
    Competencia,
    DocenteMateria,
    Periodo,
    PeriodoAnio,
    Seccion,
)
from academico.services.cierre import (
    pendientes_por_docente,
    rellenar_ceros_periodo,
)
from academico.services.estructura_minerd import crear_estructura_minerd
from administracion.models import Administrativo
from auditoria.models import Bitacora
from core.models import (
    AnioEscolar,
    CentroEducativo,
    ConfiguracionCentro,
)
from docentes.models import Docente
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario


def dj_msgs(response):
    from django.contrib import messages as dj_messages
    return list(dj_messages.get_messages(response.wsgi_request))


class BaseNotasTestCase(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Notas',
            codigo_minerd='MIN-8888',
        )
        self.config = ConfiguracionCentro.objects.create(centro=self.centro)

        self.director = self._usuario('dirnotas', 'director')
        self.secretaria = self._usuario('secnotas', 'secretaria')

        estructura = crear_estructura_minerd(self.centro, ('primaria',))
        self.grados = {g.nombre: g for g in estructura['grados']}
        self.seccion_a = Seccion.objects.create(
            centro=self.centro, nombre='A'
        )
        for grado in self.grados.values():
            self.seccion_a.grados.add(grado)

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2024-2025',
            fecha_inicio=date(2024, 8, 1),
            fecha_fin=date(2025, 7, 31),
            activo=True,
        )

        # Competencias activas del nivel (2 para simplificar los conteos).
        self.nivel_primaria = self.grados['1ro de Primaria'].nivel
        self.comps = [
            Competencia.objects.create(
                nivel=self.nivel_primaria,
                nombre=f'Competencia Test {i}',
                orden=i,
            )
            for i in (1, 2)
        ]

        self.periodo_p1 = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1,
        )
        self.periodo_completivo = Periodo.objects.create(
            centro=self.centro, nombre='COMP', orden=9, es_completivo=True,
        )

        area = AreaCurricular.objects.create(
            centro=self.centro, nombre='Área Test',
        )
        self.asignatura = Asignatura.objects.create(
            centro=self.centro, area=area, nombre='Matemática Test',
        )
        self.docente = self._docente()
        self.asignacion = self._asignar('1ro de Primaria')

    # ---------- helpers ----------

    def _usuario(self, username, rol):
        usuario = Usuario.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='clave123',
        )
        usuario.rol = rol
        usuario.save()

        # academico.views.get_centro_activo resuelve el centro vía el
        # perfil de Administrativo para director/secretaria.
        if rol in ('director', 'secretaria'):
            Administrativo.objects.create(
                usuario=usuario,
                centro=self.centro,
                primer_nombre=username.capitalize(),
                primer_apellido='Test',
                cedula=f'00{sum(ord(c) for c in username):09d}',
                sexo='F',
                fecha_nacimiento=date(1980, 1, 1),
                nacionalidad='Dominicana',
                direccion='Calle 1',
                telefono='8090000000',
                cargo=rol,
                fecha_ingreso=date(2020, 1, 1),
            )
        return usuario

    def _login(self, usuario):
        self.client.login(
            username=usuario.username, password='clave123'
        )
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _asignar(self, grado_nombre, seccion=None):
        return DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grados[grado_nombre],
            seccion=seccion or self.seccion_a,
            anio_escolar=self.anio,
        )

    def _docente(self, nombre='Docente', apellido='Prueba', cedula=None):
        return Docente.objects.create(
            centro=self.centro,
            primer_nombre=nombre,
            primer_apellido=apellido,
            cedula=cedula or f'001{abs(hash((nombre, apellido))) % 10**8:08d}A',
            sexo='F',
            fecha_nacimiento='1990-01-01',
            nacionalidad='Dominicana',
            direccion='Calle Docente',
            telefono='809-555-1111',
            codigo_docente_minerd=f'DOC-{abs(hash((nombre, apellido))) % 10**8}',
            area_especialidad='Matemática',
            fecha_ingreso='2020-08-01',
        )

    def _docente_con_usuario(self, username, nombre, apellido):
        usuario = self._usuario(username, 'docente')
        docente = self._docente(nombre, apellido)
        docente.usuario = usuario
        docente.save()
        return docente

    def _estudiante(self, matricula):
        usuario = self._usuario(f'u{matricula[-5:]}', 'estudiante')
        return Estudiante.objects.create(
            usuario=usuario,
            centro=self.centro,
            matricula=matricula,
            primer_nombre=f'Est{matricula[-2:]}',
            primer_apellido='Prueba',
            sexo='M',
            fecha_nacimiento='2012-05-10',
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor Prueba',
            cedula_tutor='00100000001',
            telefono_tutor='809-555-0000',
            parentesco_tutor='Madre',
        )

    def _inscribir(self, estudiante, grado_nombre, estado='activo'):
        return Inscripcion.objects.create(
            estudiante=estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grados[grado_nombre],
            seccion=self.seccion_a,
            estado_final=estado,
        )

    def _calificar_todo(self, inscripcion, periodo=None, nota=90):
        """Deja la calificación completa de un estudiante en un período."""
        periodo = periodo or self.periodo_p1
        for comp in self.comps:
            Calificacion.objects.create(
                inscripcion=inscripcion,
                asignatura=self.asignatura,
                competencia=comp,
                periodo=periodo,
                nota=nota,
            )

    def _abrir_periodo(self, periodo):
        estado, _ = PeriodoAnio.objects.get_or_create(
            periodo=periodo, anio_escolar=self.anio,
        )
        return estado


class ValidacionNotasPeriodoTests(BaseNotasTestCase):

    def test_detecta_estudiantes_sin_nota_completa(self):
        inscripcion = self._inscribir(
            self._estudiante('31000001'), '1ro de Primaria'
        )
        self._inscribir(self._estudiante('31000002'), '1ro de Primaria')

        # Solo una competencia cargada: falta la otra.
        Calificacion.objects.create(
            inscripcion=inscripcion,
            asignatura=self.asignatura,
            competencia=self.comps[0],
            periodo=self.periodo_p1,
            nota=85,
        )

        reporte = pendientes_por_docente(self.anio, self.periodo_p1)

        self.assertEqual(len(reporte), 1)
        fila = reporte[0]
        self.assertEqual(fila['asignatura'], 'Matemática Test')
        self.assertEqual(fila['grado'], '1ro de Primaria')
        self.assertEqual(fila['seccion'], 'A')
        # El que tiene nota parcial + el que no tiene nada.
        self.assertEqual(fila['faltantes'], 2)

    def test_sin_pendientes_cuando_todo_calificado(self):
        ins1 = self._inscribir(
            self._estudiante('31000003'), '1ro de Primaria'
        )
        ins2 = self._inscribir(
            self._estudiante('31000004'), '1ro de Primaria'
        )
        self._calificar_todo(ins1)
        self._calificar_todo(ins2)

        self.assertEqual(
            pendientes_por_docente(self.anio, self.periodo_p1), []
        )

    def test_retirados_no_exigen_nota(self):
        self._inscribir(
            self._estudiante('31000005'),
            '1ro de Primaria',
            estado='retirado',
        )

        self.assertEqual(
            pendientes_por_docente(self.anio, self.periodo_p1), []
        )

    def test_no_cruza_secciones_del_mismo_grado(self):
        seccion_b = Seccion.objects.create(
            centro=self.centro, nombre='B'
        )
        seccion_b.grados.add(self.grados['1ro de Primaria'])
        self._asignar('1ro de Primaria', seccion=seccion_b)

        # Un estudiante en cada sección del mismo grado, ambos sin notas.
        self._inscribir(self._estudiante('31000006'), '1ro de Primaria')
        ins_b = self._inscribir(
            self._estudiante('31000007'), '1ro de Primaria'
        )
        ins_b.seccion = seccion_b
        ins_b.save()

        reporte = pendientes_por_docente(self.anio, self.periodo_p1)
        self.assertEqual(len(reporte), 2)
        por_seccion = {fila['seccion']: fila['faltantes'] for fila in reporte}
        self.assertEqual(por_seccion, {'A': 1, 'B': 1})

    def test_rellenar_ceros_completa_con_origen_sistema(self):
        ins1 = self._inscribir(
            self._estudiante('31000007'), '1ro de Primaria'
        )
        ins2 = self._inscribir(
            self._estudiante('31000008'), '1ro de Primaria'
        )
        self._calificar_todo(ins1)

        creados = rellenar_ceros_periodo(self.anio, self.periodo_p1)
        self.assertEqual(creados, 2)  # 2 competencias de ins2

        self.assertTrue(
            Calificacion.objects.filter(
                inscripcion=ins2, nota=0, origen='sistema'
            ).count() == 2
        )

        # Idempotente: ya no hay pendientes ni duplica.
        self.assertEqual(
            pendientes_por_docente(self.anio, self.periodo_p1), []
        )
        self.assertEqual(
            rellenar_ceros_periodo(self.anio, self.periodo_p1), 0
        )


class CierreForzadoPeriodoViewTests(BaseNotasTestCase):

    def test_alternar_bloquea_cierre_con_pendientes(self):
        self._inscribir(self._estudiante('32000001'), '1ro de Primaria')
        estado = self._abrir_periodo(self.periodo_p1)

        self._login(self.director)
        response = self.client.post(
            reverse('alternar_periodo_anio', args=[self.periodo_p1.pk])
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertTrue(data['bloqueado'])
        self.assertEqual(len(data['pendientes']), 1)

        estado.refresh_from_db()
        self.assertFalse(estado.cerrado)

    def test_director_fuerza_cierre_y_deja_auditoria(self):
        self._inscribir(self._estudiante('32000002'), '1ro de Primaria')
        estado = self._abrir_periodo(self.periodo_p1)

        self._login(self.director)
        response = self.client.post(
            reverse('alternar_periodo_anio', args=[self.periodo_p1.pk]),
            {'forzar': '1'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        estado.refresh_from_db()
        self.assertTrue(estado.cerrado)
        self.assertEqual(
            Calificacion.objects.filter(origen='sistema').count(), 2
        )
        self.assertTrue(
            Bitacora.objects.filter(accion='CIERRE_FORZADO').exists()
        )

    def test_secretaria_no_puede_forzar(self):
        self._inscribir(self._estudiante('32000003'), '1ro de Primaria')
        estado = self._abrir_periodo(self.periodo_p1)

        self._login(self.secretaria)
        response = self.client.post(
            reverse('alternar_periodo_anio', args=[self.periodo_p1.pk]),
            {'forzar': '1'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['puede_forzar'])

        estado.refresh_from_db()
        self.assertFalse(estado.cerrado)
        self.assertFalse(Calificacion.objects.exists())

    def test_abrir_periodo_no_valida_notas(self):
        estado = self._abrir_periodo(self.periodo_p1)
        estado.cerrado = True
        estado.save()
        self._inscribir(self._estudiante('32000004'), '1ro de Primaria')

        self._login(self.secretaria)
        response = self.client.post(
            reverse('alternar_periodo_anio', args=[self.periodo_p1.pk])
        )

        self.assertEqual(response.status_code, 200)
        estado.refresh_from_db()
        self.assertFalse(estado.cerrado)

    def test_cerrar_todos_bloquea_y_forzar_funciona(self):
        self._inscribir(self._estudiante('32000005'), '1ro de Primaria')
        self._abrir_periodo(self.periodo_p1)

        url = reverse('cerrar_todos_periodos')

        # Secretaria sin notas completas: bloqueado.
        self._login(self.secretaria)
        response = self.client.get(url, follow=True)
        mensajes = [str(m) for m in dj_msgs(response)]
        self.assertTrue(any('notas pendientes' in m for m in mensajes))
        self.assertTrue(
            PeriodoAnio.objects.filter(cerrado=False).exists()
        )

        # Director con ?forzar=1: rellena y cierra.
        self._login(self.director)
        response = self.client.get(f'{url}?forzar=1', follow=True)
        mensajes = [str(m) for m in dj_msgs(response)]
        # P1 y COMP quedan abiertos tras la sincronización del catálogo:
        # el cierre masivo los cierra a ambos.
        self.assertTrue(
            any('Se cerraron 2 periodo(s)' in m for m in mensajes)
        )
        self.assertFalse(
            PeriodoAnio.objects.filter(cerrado=False).exists()
        )
        self.assertEqual(
            Calificacion.objects.filter(origen='sistema').count(), 2
        )
        self.assertTrue(
            Bitacora.objects.filter(accion='CIERRE_FORZADO').exists()
        )


class CompletivoPeriodoTests(BaseNotasTestCase):

    def test_completivo_solo_exige_recuperacion(self):
        ins_aprobado = self._inscribir(
            self._estudiante('33000001'),
            '1ro de Primaria',
            estado='aprobado',
        )
        ins_recup = self._inscribir(
            self._estudiante('33000002'),
            '1ro de Primaria',
            estado='recuperacion',
        )
        # El aprobado sí tiene notas en P1; el recuperado no.
        self._calificar_todo(ins_aprobado)

        # En P1 regular no hay pendientes (recuperado cuenta como esperado
        # también en períodos regulares).
        reporte_regular = pendientes_por_docente(
            self.anio, self.periodo_p1
        )
        self.assertEqual(len(reporte_regular), 1)
        self.assertEqual(reporte_regular[0]['faltantes'], 1)

        # En el completivo solo se le exige al de recuperación.
        reporte_comp = pendientes_por_docente(
            self.anio, self.periodo_completivo
        )
        self.assertEqual(len(reporte_comp), 1)
        self.assertEqual(
            reporte_comp[0]['inscripciones'], [ins_recup.id]
        )


class BloqueoCompletivoCierreAnioTests(BaseNotasTestCase):

    def _cerrar_anio(self):
        return self.client.get(
            reverse('cerrar_anio_escolar', args=[self.anio.pk]),
            follow=True,
        )

    def test_cierre_bloqueado_con_recuperacion_sin_procesar(self):
        self._inscribir(
            self._estudiante('34000001'),
            '1ro de Primaria',
            estado='recuperacion',
        )
        self.config.permite_completivo = True
        self.config.save()

        self._login(self.director)
        response = self._cerrar_anio()

        mensajes = [str(m) for m in dj_msgs(response)]
        self.assertTrue(
            any('completivo aún no se ha procesado' in m for m in mensajes)
        )

        self.anio.refresh_from_db()
        self.assertFalse(self.anio.cerrado)

    def test_cierre_permitido_tras_resolver_recuperaciones(self):
        self._inscribir(
            self._estudiante('34000002'), '1ro de Primaria', estado='aprobado'
        )
        self.config.permite_completivo = True
        self.config.save()

        self._login(self.director)
        self._cerrar_anio()

        self.anio.refresh_from_db()
        self.assertTrue(self.anio.cerrado)

    def test_sin_completivo_activo_no_bloquea(self):
        self._inscribir(
            self._estudiante('34000003'),
            '1ro de Primaria',
            estado='recuperacion',
        )
        self.config.permite_completivo = False
        self.config.save()

        self._login(self.director)
        self._cerrar_anio()

        self.anio.refresh_from_db()
        self.assertTrue(self.anio.cerrado)


class PreviewPromocionAdvertenciaTests(BaseNotasTestCase):

    def test_preview_avisa_recuperacion_en_plan(self):
        self._inscribir(
            self._estudiante('35000001'),
            '1ro de Primaria',
            estado='recuperacion',
        )
        self.anio.cerrar()
        self.config.permite_completivo = True
        self.config.save()

        self._login(self.director)
        response = self.client.get(
            reverse('promocion_preview', args=[self.anio.pk])
        )
        contenido = response.content.decode('utf-8')

        self.assertTrue(response.context['advertencia_completivo'])
        self.assertIn('en recuperación', contenido)

    def test_preview_sin_advertencia_sin_recuperacion(self):
        self._inscribir(
            self._estudiante('35000002'), '1ro de Primaria', estado='aprobado'
        )
        self.anio.cerrar()
        self.config.permite_completivo = True
        self.config.save()

        self._login(self.director)
        response = self.client.get(
            reverse('promocion_preview', args=[self.anio.pk])
        )

        self.assertFalse(response.context['advertencia_completivo'])


class OrigenNotaTests(BaseNotasTestCase):

    def test_default_origen_docente(self):
        inscripcion = self._inscribir(
            self._estudiante('36000001'), '1ro de Primaria'
        )
        cal = Calificacion.objects.create(
            inscripcion=inscripcion,
            asignatura=self.asignatura,
            competencia=self.comps[0],
            periodo=self.periodo_p1,
            nota=80,
        )
        self.assertEqual(cal.origen, 'docente')

    def test_docente_sobrescribe_cero_sistema_a_docente(self):
        inscripcion = self._inscribir(
            self._estudiante('36000002'), '1ro de Primaria'
        )
        cal = Calificacion.objects.create(
            inscripcion=inscripcion,
            asignatura=self.asignatura,
            competencia=self.comps[0],
            periodo=self.periodo_p1,
            nota=0,
            origen='sistema',
        )

        # El endpoint AJAX de docentes actualiza nota y origen.
        docente = self._docente_con_usuario('docajax', 'Ana', 'Docente')
        self.asignacion.docente = docente
        self.asignacion.save()

        self.client.login(username='docajax', password='clave123')

        response = self.client.post(
            reverse('guardar_notas_ajax', args=[self.asignacion.id]),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={
                'inscripcion': inscripcion.id,
                'notas': [{
                    'competencia': self.comps[0].id,
                    'periodo': self.periodo_p1.id,
                    'nota': 95,
                }],
            },
        )

        self.assertEqual(response.status_code, 200)
        cal.refresh_from_db()
        self.assertEqual(cal.nota, 95)
        self.assertEqual(cal.origen, 'docente')
