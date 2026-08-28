from datetime import date

from django.test import TestCase
from django.urls import reverse

from academico.models import (
    AreaCurricular,
    Asignatura,
    Calificacion,
    Competencia,
    DocenteMateria,
    Grado,
    Nivel,
    Periodo,
    PeriodoAnio,
    Seccion,
)
from core.models import AnioEscolar, CentroEducativo, ConfiguracionCentro, CierreAnio
from docentes.models import Docente
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario

from administracion.services.boletin import (
    construir_boletin_estudiante,
    resultado_completivo_estudiante,
    resultado_extraordinario_estudiante,
)
from promociones.services.recuperacion import (
    asignaturas_reprobadas_con_docente,
    nota_minima_estudiante,
)
from promociones.views import (
    _estado_cierre_anio,
    promociones_dashboard,
    promociones_recuperacion,
)


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


class PromocionesDashboardTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Promociones',
            codigo_minerd='MIN-PROM1',
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
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.usuario = Usuario.objects.create_user(
            username='dir_promo',
            email='dir@promo.com',
            password='clave123',
        )
        self.usuario.rol = 'director'
        self.usuario.save()

        ConfiguracionCentro.objects.create(
            centro=self.centro,
            nota_minima_aprobacion=70,
        )

    def _login(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_estado_cierre_sin_anio(self):
        self.anio.delete()
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNone(resultado)

    def test_estado_cierre_anio_activo_sin_datos(self):
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['periodos_total'], 0)
        self.assertFalse(resultado['periodos_ok'])
        self.assertEqual(resultado['boletines_total'], 0)
        self.assertTrue(resultado['boletines_ok'])
        self.assertEqual(resultado['en_recuperacion'], 0)
        self.assertTrue(resultado['completivo_ok'])
        self.assertFalse(resultado['anio_cerrado'])
        self.assertIsNone(resultado['cierre'])
        self.assertFalse(resultado['promocion_ejecutada'])

    def test_estado_cierre_periodos_cerrados(self):
        p1 = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1, es_completivo=False
        )
        PeriodoAnio.objects.create(
            periodo=p1, anio_escolar=self.anio, activo=True, cerrado=True
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['periodos_total'], 1)
        self.assertEqual(resultado['periodos_cerrados'], 1)
        self.assertTrue(resultado['periodos_ok'])

    def test_estado_cierre_periodos_abiertos(self):
        p1 = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1, es_completivo=False
        )
        PeriodoAnio.objects.create(
            periodo=p1, anio_escolar=self.anio, activo=True, cerrado=False
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['periodos_total'], 1)
        self.assertEqual(resultado['periodos_cerrados'], 0)
        self.assertFalse(resultado['periodos_ok'])

    def test_dashboard_renderiza(self):
        self._login()
        response = self.client.get(reverse('promociones:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cierre de Año Escolar y Promociones')

    def test_dashboard_sin_anio_muestra_mensaje(self):
        self._login()
        self.anio.delete()
        response = self.client.get(reverse('promociones:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay año escolar activo')

    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse('promociones:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_requiere_rol(self):
        otro = Usuario.objects.create_user(
            username='docente_promo', email='d@p.com', password='clave123'
        )
        otro.rol = 'docente'
        otro.save()
        self.client.force_login(otro)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('promociones:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_estado_cierre_con_cierre_anio(self):
        cierre = CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.usuario,
            totales={'inscritos': 0, 'aprobados': 0},
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertIsNotNone(resultado['cierre'])
        self.assertTrue(resultado['promocion_ejecutada'])

    def test_estado_cierre_fallback_año_cerrado(self):
        CierreAnio.objects.create(
            anio_escolar=self.anio,
            usuario=self.usuario,
            totales={'inscritos': 5, 'aprobados': 4},
        )
        self.anio.activo = False
        self.anio.cerrado = True
        self.anio.save()
        resultado = _estado_cierre_anio(self.centro)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['anio'], self.anio)
        self.assertTrue(resultado['anio_cerrado'])
        self.assertTrue(resultado['promocion_ejecutada'])

    def test_estado_cierre_completivo_existe(self):
        pc = Periodo.objects.create(
            centro=self.centro, nombre='Completivo', orden=10, es_completivo=True
        )
        PeriodoAnio.objects.create(
            periodo=pc, anio_escolar=self.anio, activo=True, cerrado=False
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertTrue(resultado['completivo_existe'])
        self.assertTrue(resultado['completivo_abierto'])

    def test_estado_cierre_estudiantes_en_recuperacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R1', 'Pedro', 'Gomez'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='recuperacion',
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertEqual(resultado['en_recuperacion'], 1)
        self.assertFalse(resultado['completivo_ok'])

    def test_sin_calificacion_bloquea_false_when_none(self):
        resultado = _estado_cierre_anio(self.centro)
        self.assertFalse(resultado['sin_calificacion_bloquea'])

    def test_sin_calificacion_bloquea_true_when_present(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-SC1', 'Ana', 'Lopez'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='sin_calificacion',
        )
        resultado = _estado_cierre_anio(self.centro)
        self.assertTrue(resultado['sin_calificacion_bloquea'])
        self.assertEqual(resultado['sin_calificacion'], 1)

    def test_dashboard_bloquea_paso4_con_sin_calificacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-SC2', 'Carlos', 'Ruiz'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='sin_calificacion',
        )
        self._login()
        response = self.client.get(reverse('promociones:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bloqueado')
        self.assertContains(response, 'sin calificaciones')
        self.assertContains(response, 'Resuelva antes de cerrar')


class PromocionesRecuperacionTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Recuperacion',
            codigo_minerd='MIN-REC1',
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
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='B')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro,
            nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            activo=True,
        )

        self.usuario = Usuario.objects.create_user(
            username='dir_rec',
            email='dir@rec.com',
            password='clave123',
        )
        self.usuario.rol = 'director'
        self.usuario.save()

        ConfiguracionCentro.objects.create(
            centro=self.centro,
            nota_minima_aprobacion=70,
        )

    def _login(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

    def test_recuperacion_vacia(self):
        self._login()
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay estudiantes pendientes')

    def test_recuperacion_redirect_sin_anio(self):
        self._login()
        self.anio.delete()
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 302)

    def test_recuperacion_requiere_login(self):
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 302)

    def test_recuperacion_requiere_rol(self):
        otro = Usuario.objects.create_user(
            username='docente_rec', email='d@r.com', password='clave123'
        )
        otro.rol = 'docente'
        otro.save()
        self.client.force_login(otro)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 403)

    def test_recuperacion_con_estudiante_reprobado(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R2', 'Luis', 'Torres'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='recuperacion',
        )
        self._login()
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estudiantes en Recuperación')

    def test_recuperacion_excluye_no_recuperacion(self):
        est = _crear_estudiante(
            self.centro, self.usuario, 'MAT-R3', 'Maria', 'Diaz'
        )
        Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='aprobado',
        )
        self._login()
        response = self.client.get(reverse('promociones:recuperacion'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay estudiantes pendientes')


class RecuperacionServicioTests(TestCase):

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Servicio', codigo_minerd='MIN-SRV1'
        )
        self.config = ConfiguracionCentro.objects.create(
            centro=self.centro, nota_minima_aprobacion=65
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro, nombre='Primaria', tipo='primaria'
        )
        self.grado = Grado.objects.create(nivel=self.nivel, nombre='3ro', orden=3)
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro, nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31),
            activo=True,
        )
        self.comps = [
            Competencia.objects.create(nivel=self.nivel, nombre=f'C{i}', orden=i)
            for i in (1, 2)
        ]
        self.p1 = Periodo.objects.create(centro=self.centro, nombre='P1', orden=1)
        PeriodoAnio.objects.create(
            periodo=self.p1, anio_escolar=self.anio, activo=True, cerrado=True
        )
        area = AreaCurricular.objects.create(centro=self.centro, nombre='Área Test')
        self.mates = Asignatura.objects.create(
            centro=self.centro, area=area, nombre='Matemática'
        )
        self.lengua = Asignatura.objects.create(
            centro=self.centro, area=area, nombre='Lengua Española'
        )
        self.docente = self._docente('Juan', 'Profesor')
        self.ins = self._inscripcion('recuperacion')

    def _docente(self, nombre, apellido):
        return Docente.objects.create(
            centro=self.centro,
            primer_nombre=nombre,
            primer_apellido=apellido,
            cedula=f'001{abs(hash((nombre, apellido))) % 10**8:08d}A',
            sexo='M',
            fecha_nacimiento='1980-01-01',
            nacionalidad='Dominicana',
            direccion='Calle D',
            telefono='809-555-1111',
            fecha_ingreso='2000-01-01',
            codigo_docente_minerd=f'DOC-{abs(hash((nombre, apellido))) % 10**8}',
            area_especialidad='Matemática',
        )

    def _inscripcion(self, estado):
        usuario = Usuario.objects.create_user(
            username='est_srv', email='est@serv.com', password='clave123'
        )
        est = Estudiante.objects.create(
            usuario=usuario,
            centro=self.centro,
            matricula='MAT-SRV1',
            primer_nombre='Sofia',
            primer_apellido='Reyes',
            sexo='F',
            fecha_nacimiento=date(2012, 1, 1),
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor',
            cedula_tutor='00000000000',
            telefono_tutor='8090000000',
            parentesco_tutor='Madre',
        )
        return Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final=estado,
        )

    def _calificar(self, asignatura, nota):
        for comp in self.comps:
            Calificacion.objects.create(
                inscripcion=self.ins,
                asignatura=asignatura,
                competencia=comp,
                periodo=self.p1,
                nota=nota,
                origen='docente',
            )

    def test_nota_minima_usa_el_del_nivel(self):
        self.assertIsNone(self.nivel.nota_minima_aprobacion)
        self.assertEqual(
            nota_minima_estudiante(self.ins, self.config), 65.0
        )
        self.nivel.nota_minima_aprobacion = 70
        self.nivel.save()
        self.assertEqual(
            nota_minima_estudiante(self.ins, self.config), 70.0
        )

    def test_nota_minima_fallback_minerd_por_tipo(self):
        # Incluso si el centro usa 70, primaria debe resolver a 65 según MINERD.
        self.config.nota_minima_aprobacion = 70
        self.config.save()
        self.assertIsNone(self.nivel.nota_minima_aprobacion)
        # self.nivel es de tipo primaria.
        self.assertEqual(
            nota_minima_estudiante(self.ins, self.config), 65.0
        )
        # Cambiamos el tipo a secundaria: debe resolver a 70.
        self.nivel.tipo = 'secundaria'
        self.nivel.save()
        self.assertEqual(
            nota_minima_estudiante(self.ins, self.config), 70.0
        )

    def test_cloudby_solo_la_baja_se_presenta_con_nivel(self):
        # Centro en 70 pero nivel primaria(sin valor) resuelve a 65 según
        # MINERD: 68 aprueba normal (NO va a recuperación), 58 sí.
        self.config.nota_minima_aprobacion = 70
        self.config.save()
        self._calificar(self.mates, 68)
        self._calificar(self.lengua, 58)
        DocenteMateria.objects.create(
            docente=self.docente, asignatura=self.mates,
            grado=self.grado, seccion=self.seccion, anio_escolar=self.anio,
        )
        DocenteMateria.objects.create(
            docente=self.docente, asignatura=self.lengua,
            grado=self.grado, seccion=self.seccion, anio_escolar=self.anio,
        )

        nota_minima = nota_minima_estudiante(self.ins, self.config)
        self.assertEqual(nota_minima, 65.0)
        pendientes = asignaturas_reprobadas_con_docente(
            self.ins, self.centro, self.anio, nota_minima
        )
        nombres = [p['asignatura'] for p in pendientes]
        self.assertIn('Lengua Española', nombres)
        self.assertNotIn('Matemática', nombres)

    def test_docente_no_se_duplica_por_asignatura(self):
        # Aunque el mismo docente imparte las dos asignaturas reprobadas,
        # en la columna de docentes debe listarse una sola vez.
        self._calificar(self.mates, 55)
        self._calificar(self.lengua, 50)
        DocenteMateria.objects.create(
            docente=self.docente, asignatura=self.mates,
            grado=self.grado, seccion=self.seccion, anio_escolar=self.anio,
        )
        DocenteMateria.objects.create(
            docente=self.docente, asignatura=self.lengua,
            grado=self.grado, seccion=self.seccion, anio_escolar=self.anio,
        )

        pendientes = asignaturas_reprobadas_con_docente(
            self.ins, self.centro, self.anio, 65
        )
        self.assertEqual(len(pendientes), 2)
        # Deduplicación idéntica a la que hace la vista al rendender.
        docentes = [
            d['docente'] for d in pendientes
            if d['docente']
        ]
        self.assertEqual(len(set(docentes)), 1)
        self.assertEqual(
            {' '.join(str(d['docente']).split()) for d in pendientes},
            {'Juan Profesor'},
        )


class ResultadoCompletivoExtraordinarioTests(TestCase):
    """Prueba las fórmulas MINERD de completivas y extraordinarias.

    Completiva (Art. 51/80): final = (nota_completivo*0.50) + (pf*0.50).
    Extraordinaria (Art. 52/81): final = (nota_extraordinario*0.70) + (pf*0.30).
    """

    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Comple Extra', codigo_minerd='MIN-CEXT1'
        )
        ConfiguracionCentro.objects.create(
            centro=self.centro, nota_minima_aprobacion=65
        )
        self.nivel = Nivel.objects.create(
            centro=self.centro, nombre='Primaria', tipo='primaria'
        )
        self.grado = Grado.objects.create(
            nivel=self.nivel, nombre='3ro', orden=3
        )
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.anio = AnioEscolar.objects.create(
            centro=self.centro, nombre='2026-2027',
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31),
            activo=True,
        )
        self.comp = Competencia.objects.create(
            nivel=self.nivel, nombre='C1', orden=1
        )
        self.periodos = []
        for i in range(1, 5):
            p = Periodo.objects.create(
                centro=self.centro, nombre=f'P{i}', orden=i
            )
            PeriodoAnio.objects.create(
                periodo=p, anio_escolar=self.anio, activo=True, cerrado=True
            )
            self.periodos.append(p)
        area = AreaCurricular.objects.create(centro=self.centro, nombre='Área')
        self.mates = Asignatura.objects.create(
            centro=self.centro, area=area, nombre='Matemática'
        )
        self.docente = Docente.objects.create(
            centro=self.centro,
            primer_nombre='Ana',
            primer_apellido='Maestra',
            cedula='00100012345A',
            sexo='F',
            fecha_nacimiento='1985-01-01',
            nacionalidad='Dominicana',
            direccion='Calle D',
            telefono='809-555-0000',
            fecha_ingreso='2005-01-01',
            codigo_docente_minerd='DOC-CEXT1',
            area_especialidad='Matemática',
        )
        DocenteMateria.objects.create(
            docente=self.docente,
            asignatura=self.mates,
            grado=self.grado,
            seccion=self.seccion,
            anio_escolar=self.anio,
        )

        usuario = Usuario.objects.create_user(
            username='est_cext', email='est@cext.com', password='clave123'
        )
        est = Estudiante.objects.create(
            usuario=usuario,
            centro=self.centro,
            matricula='MAT-CEXT1',
            primer_nombre='Mario',
            primer_apellido='Pena',
            sexo='M',
            fecha_nacimiento=date(2012, 1, 1),
            lugar_nacimiento='Santo Domingo',
            nacionalidad='Dominicana',
            direccion='Calle 1',
            nombre_tutor='Tutor',
            cedula_tutor='00000000000',
            telefono_tutor='8090000000',
            parentesco_tutor='Madre',
        )
        self.ins = Inscripcion.objects.create(
            estudiante=est,
            centro=self.centro,
            anio_escolar=self.anio,
            grado=self.grado,
            seccion=self.seccion,
            estado_final='recuperacion',
        )

    def _calificar_periodos(self, notas_por_periodo):
        for p, nota in zip(self.periodos, notas_por_periodo):
            Calificacion.objects.create(
                inscripcion=self.ins,
                asignatura=self.mates,
                competencia=self.comp,
                periodo=p,
                nota=nota,
                origen='docente',
            )

    def _calificar_completivo(self, nota):
        pc = Periodo.objects.create(
            centro=self.centro, nombre='Completivo', orden=10,
            es_completivo=True,
        )
        PeriodoAnio.objects.create(
            periodo=pc, anio_escolar=self.anio, activo=True, cerrado=True
        )
        Calificacion.objects.create(
            inscripcion=self.ins,
            asignatura=self.mates,
            competencia=self.comp,
            periodo=pc,
            nota=nota,
            origen='docente',
        )
        return pc

    def _calificar_extraordinario(self, nota):
        pe = Periodo.objects.create(
            centro=self.centro, nombre='Extraordinario', orden=11,
            es_extraordinario=True,
        )
        PeriodoAnio.objects.create(
            periodo=pe, anio_escolar=self.anio, activo=True, cerrado=True
        )
        Calificacion.objects.create(
            inscripcion=self.ins,
            asignatura=self.mates,
            competencia=self.comp,
            periodo=pe,
            nota=nota,
            origen='docente',
        )
        return pe

    def test_completivo_usar_formula_50_50(self):
        # pf = 60 (reprobada en primaria, min 65). Completivo = 69.
        # Directo: 69 >= 65 parecería aprobar, pero la fórmula 50/50 da
        # (69*0.5)+(60*0.5) = 64.5 < 65 -> NO aprueba.
        self._calificar_periodos([60, 60, 60, 60])
        self._calificar_completivo(69)
        resultado = resultado_completivo_estudiante(
            self.ins, self.centro, self.anio, 65
        )
        self.assertEqual(resultado['aprobado'], False)
        self.assertEqual(resultado['detalle'][0]['final'], 64.5)

    def test_completivo_aprueba_con_formula(self):
        # pf = 60, completivo = 70 -> (70*0.5)+(60*0.5) = 65 >= 65 -> aprueba.
        self._calificar_periodos([60, 60, 60, 60])
        self._calificar_completivo(70)
        resultado = resultado_completivo_estudiante(
            self.ins, self.centro, self.anio, 65
        )
        self.assertTrue(resultado['aprobado'])
        self.assertEqual(resultado['detalle'][0]['final'], 65)

    def test_extraordinario_usar_formula_70_30(self):
        # pf = 60, extraordinario = 66. Directo: 66 >= 65 parecería aprobar,
        # pero la fórmula 70/30 da (66*0.7)+(60*0.3) = 64.2 < 65 -> NO aprueba.
        self._calificar_periodos([60, 60, 60, 60])
        self._calificar_extraordinario(66)
        resultado = resultado_extraordinario_estudiante(
            self.ins, self.centro, self.anio, 65
        )
        self.assertFalse(resultado['aprobado'])
        self.assertEqual(resultado['detalle'][0]['final'], 64.2)

    def test_extraordinario_aprueba_con_formula(self):
        # pf = 60, extraordinario = 68 -> (68*0.7)+(60*0.3) = 65.6 >= 65.
        self._calificar_periodos([60, 60, 60, 60])
        self._calificar_extraordinario(68)
        resultado = resultado_extraordinario_estudiante(
            self.ins, self.centro, self.anio, 65
        )
        self.assertTrue(resultado['aprobado'])
        self.assertEqual(resultado['detalle'][0]['final'], 65.6)

    def test_pf_sigue_igual_a_promedio_de_periodos(self):
        # Verifica que el cálculo base (PC y PF) no cambió con la normativa.
        self._calificar_periodos([80, 70, 90, 60])
        boletin = construir_boletin_estudiante(
            self.ins, self.centro, self.anio
        )
        asignatura = boletin['asignaturas'][0]
        self.assertEqual(asignatura['competencias'][0]['pc'], 75)
        self.assertEqual(asignatura['pf'], 75)
