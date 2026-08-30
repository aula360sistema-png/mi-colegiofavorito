from datetime import date

from django.core.cache import cache
from django.test import TestCase

from academico.models import (
    AreaCurricular,
    Asignatura,
    Calificacion,
    Competencia,
    DocenteMateria,
    Grado,
    Nivel,
    Periodo,
    Seccion,
)
from asistencia.models import AsistenciaEstudiante
from core.models import AnioEscolar, CentroEducativo
from docentes.models import Docente
from estudiantes.models import Estudiante, Inscripcion
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


def _crear_docente(centro, cedula, nombre, apellido, estado='activo'):
    return Docente.objects.create(
        centro=centro,
        primer_nombre=nombre,
        primer_apellido=apellido,
        cedula=cedula,
        sexo='F',
        fecha_nacimiento=date(1985, 5, 5),
        nacionalidad='Dominicana',
        direccion='Calle 2',
        telefono='8091112222',
        codigo_docente_minerd='DOC-' + cedula,
        area_especialidad='Matemática',
        fecha_ingreso=date(2020, 8, 1),
        tipo_contrato='contratado',
        tanda='matutina',
        estado=estado,
    )


class ReportesAsistenciaTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0007',
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
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
        self.grado.secciones.add(self.seccion)

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.director = Usuario.objects.create_user(
            username='directorrep1',
            email='directorrep@test.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

        self.estudiante = _crear_estudiante(
            self.centro,
            Usuario.objects.create_user(
                username='estrep1',
                email='estrep1@test.com',
                password='clave123',
            ),
            'MAT-0009',
            'Carlos',
            'Reyes',
        )

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )

        AsistenciaEstudiante.objects.create(
            inscripcion=self.inscripcion,
            fecha=date(2026, 5, 6),
            estado='presente',
        )
        AsistenciaEstudiante.objects.create(
            inscripcion=self.inscripcion,
            fecha=date(2026, 5, 7),
            estado='ausente',
        )

    def _login(self, usuario):
        self.client.login(username=usuario.username, password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_pantalla_asistencia_responde(self):
        self._login(self.director)

        response = self.client.get('/reportes/asistencia/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reporte de asistencia')

    def test_reporte_asistencia_integrado_en_reportes(self):
        self._login(self.director)

        url = (
            '/reportes/'
            f'?anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reporte de asistencia')
        self.assertContains(response, '/reportes/asistencia/')
        self.assertContains(response, 'Carga académica de docentes')
        self.assertContains(response, '/reportes/carga-academica/')
        self.assertContains(response, 'Acta de sección')
        self.assertContains(response, 'Listado de estudiantes')

    def test_hub_organizado_en_pestanas(self):
        self._login(self.director)

        response = self.client.get('/reportes/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reportes disponibles')
        self.assertContains(response, 'Consulta de estudiantes')
        self.assertContains(response, 'Estadísticas')
        # La pestaña por defecto es "Reportes disponibles": su panel visible
        # y el resto ocultos.
        self.assertContains(response, 'id="tab-disponibles" class="tab-panel p-6"')
        self.assertContains(response, 'id="tab-consultas" class="hidden tab-panel')
        self.assertContains(response, 'id="tab-metricas" class="hidden tab-panel')

    def test_hub_pestana_metricas(self):
        self._login(self.director)

        response = self.client.get('/reportes/?tab=metricas')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matrícula por grado y sección')
        self.assertContains(response, 'Estados académicos')
        self.assertContains(response, 'id="tab-metricas" class="tab-panel p-6"')
        self.assertContains(response, 'id="tab-disponibles" class="hidden tab-panel')

    def test_hub_pestana_consultas_preserva_filtros(self):
        self._login(self.director)

        url = (
            '/reportes/'
            f'?tab=consultas&anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tab-consultas" class="tab-panel"')
        self.assertContains(response, 'Acta de sección')
        self.assertContains(response, 'Listado de estudiantes')

    def test_hub_pestana_desconocida_vuelve_a_disponibles(self):
        self._login(self.director)

        response = self.client.get('/reportes/?tab=otra')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tab-disponibles" class="tab-panel p-6"')

    def test_listado_seccion_imprimible(self):
        self._login(self.director)

        url = (
            '/reportes/listado-seccion/imprimir/'
            f'?anio={self.anio.id}&grado={self.grado.id}&seccion={self.seccion.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Listado de estudiantes')
        self.assertContains(response, 'MAT-0009')
        self.assertContains(response, 'Reyes')
        self.assertContains(response, 'Carlos')

    def test_resumen_asistencia_por_estudiante(self):
        self._login(self.director)

        url = (
            '/reportes/asistencia/imprimir/'
            f'?tipo=estudiante&anio={self.anio.id}'
            f'&estudiante_id={self.estudiante.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reporte de asistencia del estudiante')
        self.assertContains(response, 'Carlos')
        self.assertContains(response, 'Reyes')
        self.assertContains(response, 'Presente 1')
        self.assertContains(response, 'Ausente 1')

    def test_planilla_mensual_por_seccion(self):
        self._login(self.director)

        url = (
            '/reportes/asistencia/imprimir/'
            f'?tipo=seccion&anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}&mes=5'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planilla de asistencia mensual')
        self.assertContains(response, 'Carlos')
        self.assertContains(response, 'Reyes')

    def test_resumen_anual_por_seccion(self):
        self._login(self.director)

        url = (
            '/reportes/asistencia/imprimir/'
            f'?tipo=seccion&anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resumen de asistencia')
        self.assertContains(response, 'MAT-0009')

    def test_estudiante_sin_inscripcion_muestra_error(self):
        self._login(self.director)

        otro = Usuario.objects.create_user(
            username='sinesc',
            email='sinesc@test.com',
            password='clave123',
        )
        sin_inscripcion = _crear_estudiante(
            self.centro,
            otro,
            'MAT-0010',
            'Luis',
            'Diaz',
        )

        url = (
            '/reportes/asistencia/imprimir/'
            f'?tipo=estudiante&anio={self.anio.id}'
            f'&estudiante_id={sin_inscripcion.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no tiene inscripción')

    def test_docente_puede_consultar_dentro_del_alcance(self):
        docente = Usuario.objects.create_user(
            username='docrep1',
            email='docrep1@test.com',
            password='clave123',
        )
        docente.rol = 'docente'
        docente.save()

        registro_docente = _crear_docente(self.centro, '001-0000000-9', 'Rosa', 'Perez')
        registro_docente.usuario = docente
        registro_docente.save()

        DocenteMateria.objects.create(
            docente=registro_docente,
            asignatura=Asignatura.objects.create(
                centro=self.centro,
                area=AreaCurricular.objects.create(centro=self.centro, nombre='Ciencias'),
                nombre='Matemática',
            ),
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio,
        )

        self._login(docente)

        response = self.client.get('/reportes/asistencia/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reporte de asistencia')


class CargaAcademicaTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0008',
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria',
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='2do',
            orden=2,
        )
        self.seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='B',
        )
        self.grado.secciones.add(self.seccion)

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.director = Usuario.objects.create_user(
            username='directorcarga1',
            email='directorcarga@test.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

        self.docente = _crear_docente(
            self.centro,
            '001-0000000-1',
            'Ana',
            'Lopez',
        )
        self.docente_sin_carga = _crear_docente(
            self.centro,
            '001-0000000-2',
            'Pedro',
            'Martinez',
        )
        self.docente_inactivo = _crear_docente(
            self.centro,
            '001-0000000-3',
            'Luis',
            'Gomez',
            estado='inactivo',
        )

        self.area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Ciencias',
        )
        self.asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=self.area,
            nombre='Matemática',
        )
        self.asignacion = DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio,
        )

    def _login(self, usuario):
        self.client.login(username=usuario.username, password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_pantalla_carga_academica_responde(self):
        self._login(self.director)

        response = self.client.get('/reportes/carga-academica/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carga académica de docentes')

    def test_pantalla_muestra_asignaciones(self):
        self._login(self.director)

        url = f'/reportes/carga-academica/?anio={self.anio.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Lopez')
        self.assertContains(response, 'Matemática')

    def test_print_carga_academica(self):
        self._login(self.director)

        url = f'/reportes/carga-academica/imprimir/?anio={self.anio.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carga académica de docentes')
        self.assertContains(response, 'Matemática')
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Lopez')

    def test_docente_sin_carga_muestra_aviso(self):
        self._login(self.director)

        url = f'/reportes/carga-academica/?anio={self.anio.id}'
        response = self.client.get(url)

        self.assertContains(response, 'Sin asignaciones en este año escolar.')
        self.assertContains(response, 'Pedro')
        self.assertContains(response, 'Martinez')

    def test_docente_inactivo_excluido(self):
        self._login(self.director)

        url = f'/reportes/carga-academica/?anio={self.anio.id}'
        response = self.client.get(url)

        self.assertNotContains(response, 'Gomez')

    def test_filtro_por_docente(self):
        self._login(self.director)

        url = (
            '/reportes/carga-academica/'
            f'?anio={self.anio.id}&docente_id={self.docente.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matemática')
        self.assertNotContains(response, 'Sin asignaciones en este año escolar.')

    def test_docente_consulta_su_carga_academica(self):
        docente = Usuario.objects.create_user(
            username='docrep2',
            email='docrep2@test.com',
            password='clave123',
        )
        docente.rol = 'docente'
        docente.save()

        self.docente.usuario = docente
        self.docente.save()

        self._login(docente)

        response = self.client.get('/reportes/carga-academica/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matemática')
        self.assertNotContains(response, 'Sin asignaciones en este año escolar.')


class CalificacionesTests(TestCase):

    def setUp(self):
        cache.clear()

        self.centro = CentroEducativo.objects.create(
            nombre='Colegio de Prueba',
            codigo_minerd='MIN-0010',
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro,
            nombre='Primaria',
            tipo='primaria',
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel,
            nombre='3ro',
            orden=3,
        )
        self.seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='A',
        )
        self.grado.secciones.add(self.seccion)

        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.periodo = Periodo.objects.create(
            centro=self.centro,
            nombre='P1',
            orden=1,
        )

        self.director = Usuario.objects.create_user(
            username='directorcal1',
            email='directorcal@test.com',
            password='clave123',
        )
        self.director.rol = 'director'
        self.director.save()

        self.estudiante = _crear_estudiante(
            self.centro,
            Usuario.objects.create_user(
                username='estcal1',
                email='estcal1@test.com',
                password='clave123',
            ),
            'MAT-0011',
            'Ana',
            'Suarez',
        )

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )

        self.area = AreaCurricular.objects.create(
            centro=self.centro,
            nombre='Ciencias',
        )
        self.asignatura = Asignatura.objects.create(
            centro=self.centro,
            area=self.area,
            nombre='Matemática',
        )
        self.competencia_1 = Competencia.objects.create(
            nivel=self.nivel,
            nombre='Resolución de problemas',
            orden=1,
            activo=True,
        )
        self.competencia_2 = Competencia.objects.create(
            nivel=self.nivel,
            nombre='Comunicación matemática',
            orden=2,
            activo=True,
        )

        self.docente = _crear_docente(
            self.centro,
            '001-0000010-1',
            'Carmen',
            'Urena',
        )
        DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio,
        )

        self._notas(80, 60)

    def _notas(self, n1, n2):
        Calificacion.objects.create(
            inscripcion=self.inscripcion,
            asignatura=self.asignatura,
            competencia=self.competencia_1,
            periodo=self.periodo,
            nota=n1,
        )
        Calificacion.objects.create(
            inscripcion=self.inscripcion,
            asignatura=self.asignatura,
            competencia=self.competencia_2,
            periodo=self.periodo,
            nota=n2,
        )

    def _login(self, usuario):
        self.client.login(username=usuario.username, password='clave123')
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def _url_planilla(self):
        return (
            '/reportes/calificaciones/'
            f'?anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}&periodo={self.periodo.id}'
        )

    def test_pantalla_calificaciones_responde(self):
        self._login(self.director)

        response = self.client.get('/reportes/calificaciones/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calificaciones por período')

    def test_planilla_muestra_notas_promedio_y_estado(self):
        self._login(self.director)

        response = self.client.get(self._url_planilla())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Suarez')
        self.assertContains(response, 'Matemática')
        self.assertContains(response, '70')
        self.assertContains(response, 'Aprobado')

    def test_planilla_reprobado_bajo_la_nota_minima(self):
        otro = Usuario.objects.create_user(
            username='estcal2',
            email='estcal2@test.com',
            password='clave123',
        )
        estudiante = _crear_estudiante(
            self.centro,
            otro,
            'MAT-0012',
            'Luis',
            'Tavares',
        )
        inscripcion = Inscripcion.objects.create(
            estudiante=estudiante,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
        )
        Calificacion.objects.create(
            inscripcion=inscripcion,
            asignatura=self.asignatura,
            competencia=self.competencia_1,
            periodo=self.periodo,
            nota=40,
        )
        Calificacion.objects.create(
            inscripcion=inscripcion,
            asignatura=self.asignatura,
            competencia=self.competencia_2,
            periodo=self.periodo,
            nota=50,
        )

        self._login(self.director)

        response = self.client.get(self._url_planilla())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luis')
        self.assertContains(response, '45')
        self.assertContains(response, 'Reprobado')

    def test_boleta_periodo_muestra_competencias(self):
        self._login(self.director)

        url = (
            f'/reportes/boleta/{self.inscripcion.id}/{self.periodo.id}/'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Matemática')
        self.assertContains(response, 'Resolución de problemas')
        self.assertContains(response, 'Comunicación matemática')
        self.assertContains(response, '70')
        self.assertContains(response, 'Aprobado')

    def test_print_planilla_calificaciones(self):
        self._login(self.director)

        url = (
            '/reportes/calificaciones/imprimir/'
            f'?anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={self.seccion.id}&periodo={self.periodo.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planilla de calificaciones')
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Suarez')

    def test_print_boleta_periodo(self):
        self._login(self.director)

        url = (
            '/reportes/boleta/imprimir/'
            f'?inscripcion_id={self.inscripcion.id}'
            f'&periodo_id={self.periodo.id}'
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Boleta de calificaciones del período')
        self.assertContains(response, 'Resolución de problemas')

    def test_acceso_docente_restringido_a_sus_secciones(self):
        docente = Usuario.objects.create_user(
            username='doccal1',
            email='doccal1@test.com',
            password='clave123',
        )
        docente.rol = 'docente'
        docente.save()
        self.docente.usuario = docente
        self.docente.save()

        otra_seccion = Seccion.objects.create(
            centro=self.centro,
            nombre='B',
        )
        self.grado.secciones.add(otra_seccion)

        otro_docente = _crear_docente(
            self.centro,
            '001-0000010-2',
            'Raul',
            'Fernandez',
        )
        DocenteMateria.objects.create(
            docente=otro_docente,
            asignatura=self.asignatura,
            grado=self.grado,
            seccion=otra_seccion,
            anio_escolar=self.anio,
        )

        self._login(docente)

        response = self.client.get(self._url_planilla())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')

        url = (
            '/reportes/calificaciones/'
            f'?anio={self.anio.id}&grado={self.grado.id}'
            f'&seccion={otra_seccion.id}&periodo={self.periodo.id}'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)