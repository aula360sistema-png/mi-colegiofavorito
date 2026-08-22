from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from academico.models import Nivel, Periodo, PeriodoAnio, Seccion
from core.models import AnioEscolar, CentroEducativo
from estudiantes.models import Estudiante, Inscripcion

from .models import (
    DestrezaCognitiva,
    DiagnosticoCognitivo,
    Ejercicio,
    MetricaCognitiva,
    PlanRefuerzo,
    SesionEntrenamiento,
    TramoEdad,
    UnidadEntrenamiento,
)
from .services import (
    diagnosticos_del_centro,
    invalidar_catalogo,
    invalidar_entrenamiento,
    metricas_del_centro,
    planes_refuerzo_del_centro,
    sesiones_del_centro,
    tramos_disponibles,
    destrezas_por_tramo,
    unidades_por_tramo,
)

Usuario = get_user_model()


class BaseEntrenamientoTestCase(TestCase):
    def setUp(self):
        self.centro = CentroEducativo.objects.create(
            nombre='Colegio Entrenamiento', direccion='Calle 10',
            telefono='8091234567', email='ent@test.com',
        )
        self.anio = AnioEscolar.objects.create(
            centro=self.centro, nombre='2026-2027',
            fecha_inicio=date(2026, 8, 20), fecha_fin=date(2027, 6, 30),
            activo=True,
        )
        self.director = Usuario.objects.create_user(
            username='dir_ent', email='dir_ent@test.com', password='Clave123A!',
        )
        self.director.rol = 'director'
        self.director.save()
        self.client.force_login(self.director)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()

        self.estudiante_user = Usuario.objects.create_user(
            username='est_ent', email='est_ent@test.com', password='Clave123A!',
        )
        self.estudiante_user.rol = 'estudiante'
        self.estudiante_user.save()
        self.estudiante = Estudiante.objects.create(
            usuario=self.estudiante_user, centro=self.centro,
            matricula='MAT-ENT-001', primer_nombre='Ana', primer_apellido='Rios',
            sexo='F', fecha_nacimiento=date(2014, 3, 15),
            lugar_nacimiento='Santiago', nacionalidad='Dominicana',
            direccion='Calle 5', nombre_tutor='Luis Rios',
            cedula_tutor='40233344455', telefono_tutor='8093334455',
            parentesco_tutor='Padre',
        )

        self.nivel = Nivel.objects.create(
            centro=self.centro, nombre='Primaria', tipo='primaria',
        )
        self.grado = self.nivel.grado_set.create(nombre='Tercero', orden=3)
        self.seccion = Seccion.objects.create(centro=self.centro, nombre='A')
        self.grado.secciones.add(self.seccion)

        self.inscripcion = Inscripcion.objects.create(
            estudiante=self.estudiante, centro=self.centro,
            anio_escolar=self.anio, grado=self.grado,
            seccion=self.seccion,
        )

        self.tramo = TramoEdad.objects.create(
            nombre='Tramo 7-9', edad_min=7, edad_max=9, orden=1,
        )
        self.destreza = DestrezaCognitiva.objects.create(
            tramo=self.tramo, categoria='atencion',
            nombre='Atención sostenida', orden=1,
        )
        self.unidad = UnidadEntrenamiento.objects.create(
            tramo=self.tramo, numero=1, nombre='Unidad A',
        )
        self.unidad.destrezas.add(self.destreza)

        self.periodo = Periodo.objects.create(
            centro=self.centro, nombre='P1', orden=1,
        )
        self.periodo_anio = PeriodoAnio.objects.create(
            periodo=self.periodo, anio_escolar=self.anio,
        )

    def _make_ejercicio(self):
        return Ejercicio.objects.create(
            unidad=self.unidad, destreza=self.destreza,
            tipo='seleccion', dificultad=1,
            enunciado='¿Cuánto es 2+2?',
            opciones=[{'texto': 'Cuatro', 'correcta': True}],
            tiempo_max_seg=30,
        )

    def _make_diagnostico(self):
        return DiagnosticoCognitivo.objects.create(
            estudiante=self.estudiante, anio_escolar=self.anio,
            tramo=self.tramo,
            resultado={'1': {'aciertos': 5, 'errores': 2, 'nivel': 'medio'}},
        )

    def _make_sesion(self, unidad=None):
        return SesionEntrenamiento.objects.create(
            estudiante=self.estudiante, anio_escolar=self.anio,
            unidad=unidad or self.unidad,
            duracion_seg=120, items_total=10,
            aciertos=7, errores=3, estado='completada',
        )

    def _make_metrica(self):
        return MetricaCognitiva.objects.create(
            estudiante=self.estudiante, anio_escolar=self.anio,
            periodo=self.periodo_anio, tramo=self.tramo,
            fecha_corte=date(2027, 1, 15),
            ipd=Decimal('72.50'), percentil_edad=Decimal('65.00'),
            desglose={'1': {'aciertos': 8, 'errores': 2}},
        )

    def _make_plan(self):
        return PlanRefuerzo.objects.create(
            estudiante=self.estudiante, anio_escolar=self.anio,
            unidad=self.unidad, generado_por='auto',
            origen='destrezas_bajas', estado='pendiente',
        )


# ---------------------------------------------------------------------------
# 1. CacheEntrenamientoTests (4 tests)
# ---------------------------------------------------------------------------
class CacheEntrenamientoTests(BaseEntrenamientoTestCase):

    def test_diagnosticos_cache_segunda_llamada_sin_queries(self):
        cache.clear()
        diagnosticos_del_centro(self.centro, self.anio)
        with self.assertNumQueries(0):
            diagnosticos_del_centro(self.centro, self.anio)

    def test_sesiones_cache_segunda_llamada_sin_queries(self):
        cache.clear()
        sesiones_del_centro(self.centro, self.anio)
        with self.assertNumQueries(0):
            sesiones_del_centro(self.centro, self.anio)

    def test_invalidar_entrenamiento_invalida_cache(self):
        cache.clear()
        diagnosticos_del_centro(self.centro, self.anio)
        invalidar_entrenamiento(self.centro.id)
        with self.assertNumQueries(1):
            diagnosticos_del_centro(self.centro, self.anio)

    def test_metricas_cache_segunda_llamada_sin_queries(self):
        cache.clear()
        metricas_del_centro(self.centro, self.anio)
        with self.assertNumQueries(0):
            metricas_del_centro(self.centro, self.anio)


# ---------------------------------------------------------------------------
# 2. CatalogoTests (5 tests)
# ---------------------------------------------------------------------------
class CatalogoTests(BaseEntrenamientoTestCase):

    def test_tramos_disponibles_devuelve_lista(self):
        resultado = tramos_disponibles()
        self.assertIsInstance(resultado, list)
        self.assertGreaterEqual(len(resultado), 1)
        self.assertIn(self.tramo, resultado)

    def test_destrezas_por_tramo(self):
        resultado = destrezas_por_tramo(self.tramo.id)
        self.assertIsInstance(resultado, list)
        self.assertIn(self.destreza, resultado)

    def test_unidades_por_tramo(self):
        resultado = unidades_por_tramo(self.tramo.id)
        self.assertIsInstance(resultado, list)
        self.assertIn(self.unidad, resultado)

    def test_tramos_cache_segunda_llamada_sin_queries(self):
        cache.clear()
        tramos_disponibles()
        with self.assertNumQueries(0):
            tramos_disponibles()

    def test_invalidar_catalogo_fuerza_reconsulta(self):
        cache.clear()
        tramos_disponibles()
        invalidar_catalogo()
        with self.assertNumQueries(1):
            tramos_disponibles()


# ---------------------------------------------------------------------------
# 3. DashboardTests (2 tests)
# ---------------------------------------------------------------------------
class DashboardTests(BaseEntrenamientoTestCase):

    def test_dashboard_renders(self):
        response = self.client.get(reverse('entrenamiento:inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entrenamiento Cognitivo')

    def test_dashboard_metricas(self):
        response = self.client.get(reverse('entrenamiento:inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Diagnósticos')


# ---------------------------------------------------------------------------
# 4. DestrezaCRUDTests (4 tests)
# ---------------------------------------------------------------------------
class DestrezaCRUDTests(BaseEntrenamientoTestCase):

    def test_destreza_list_renders(self):
        response = self.client.get(reverse('entrenamiento:destreza_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Destrezas Cognitivas')

    def test_destreza_create(self):
        response = self.client.post(reverse('entrenamiento:destreza_create'), {
            'tramo': self.tramo.id,
            'categoria': 'memoria',
            'nombre': 'Memoria de trabajo',
            'descripcion': 'Prueba de memoria',
            'orden': 2,
            'activo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            DestrezaCognitiva.objects.filter(nombre='Memoria de trabajo').exists()
        )

    def test_destreza_update(self):
        response = self.client.post(
            reverse('entrenamiento:destreza_update', args=[self.destreza.id]),
            {
                'tramo': self.tramo.id,
                'categoria': 'lectura',
                'nombre': 'Atención dividida',
                'descripcion': 'Actualizado',
                'orden': 1,
                'activo': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.destreza.refresh_from_db()
        self.assertEqual(self.destreza.nombre, 'Atención dividida')

    def test_destreza_delete(self):
        response = self.client.post(
            reverse('entrenamiento:destreza_delete', args=[self.destreza.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DestrezaCognitiva.objects.filter(pk=self.destreza.id).exists())


# ---------------------------------------------------------------------------
# 5. DiagnosticoTests (4 tests)
# ---------------------------------------------------------------------------
class DiagnosticoTests(BaseEntrenamientoTestCase):

    def test_diagnostico_list_renders(self):
        response = self.client.get(reverse('entrenamiento:diagnostico_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Diagnósticos Cognitivos')

    def test_diagnostico_create(self):
        DiagnosticoCognitivo.objects.filter(
            estudiante=self.estudiante, anio_escolar=self.anio,
        ).delete()
        response = self.client.post(reverse('entrenamiento:diagnostico_create'), {
            'estudiante': self.estudiante.id,
            'anio_escolar': self.anio.id,
            'tramo': self.tramo.id,
            'resultado': '{"1": {"aciertos": 8, "errores": 2, "nivel": "alto"}}',
            'ipd': '85.50',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            DiagnosticoCognitivo.objects.filter(
                estudiante=self.estudiante, anio_escolar=self.anio,
            ).exists()
        )

    def test_diagnostico_detail_renders(self):
        diag = self._make_diagnostico()
        response = self.client.get(
            reverse('entrenamiento:diagnostico_detail', args=[diag.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')

    def test_diagnostico_delete(self):
        diag = self._make_diagnostico()
        response = self.client.post(
            reverse('entrenamiento:diagnostico_delete', args=[diag.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DiagnosticoCognitivo.objects.filter(pk=diag.id).exists())


# ---------------------------------------------------------------------------
# 6. EjercicioCRUDTests (3 tests)
# ---------------------------------------------------------------------------
class EjercicioCRUDTests(BaseEntrenamientoTestCase):

    def test_ejercicio_list_renders(self):
        response = self.client.get(reverse('entrenamiento:ejercicio_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ejercicios')

    def test_ejercicio_create(self):
        response = self.client.post(reverse('entrenamiento:ejercicio_create'), {
            'unidad': self.unidad.id,
            'destreza': self.destreza.id,
            'tipo': 'seleccion',
            'dificultad': 2,
            'enunciado': '¿Cuál es la capital de RD?',
            'texto': '',
            'opciones': '[{"texto": "Santo Domingo", "correcta": true}, {"texto": "Santiago", "correcta": false}]',
            'respuesta_correcta': '',
            'tiempo_max_seg': 45,
            'activo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Ejercicio.objects.filter(
                enunciado='¿Cuál es la capital de RD?',
            ).exists()
        )

    def test_ejercicio_detail_renders(self):
        ej = self._make_ejercicio()
        response = self.client.get(
            reverse('entrenamiento:ejercicio_detail', args=[ej.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '¿Cuánto es 2+2?')


# ---------------------------------------------------------------------------
# 7. MetricaTests (2 tests)
# ---------------------------------------------------------------------------
class MetricaTests(BaseEntrenamientoTestCase):

    def test_metrica_list_renders(self):
        response = self.client.get(reverse('entrenamiento:metrica_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Métricas Cognitivas')

    def test_metrica_detail_renders(self):
        metrica = self._make_metrica()
        response = self.client.get(
            reverse('entrenamiento:metrica_detail', args=[metrica.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')


# ---------------------------------------------------------------------------
# 8. PlanRefuerzoTests (5 tests)
# ---------------------------------------------------------------------------
class PlanRefuerzoTests(BaseEntrenamientoTestCase):

    def test_plan_list_renders(self):
        response = self.client.get(reverse('entrenamiento:plan_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planes de Refuerzo')

    def test_plan_create(self):
        response = self.client.post(reverse('entrenamiento:plan_create'), {
            'estudiante': self.estudiante.id,
            'anio_escolar': self.anio.id,
            'unidad': self.unidad.id,
            'generado_por': 'docente',
            'origen': 'alerta',
            'estado': 'pendiente',
            'nota': 'Plan de prueba',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PlanRefuerzo.objects.filter(
                estudiante=self.estudiante, nota='Plan de prueba',
            ).exists()
        )

    def test_plan_detail_renders(self):
        plan = self._make_plan()
        response = self.client.get(
            reverse('entrenamiento:plan_detail', args=[plan.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')

    def test_plan_update_estado(self):
        plan = self._make_plan()
        response = self.client.post(
            reverse('entrenamiento:plan_update_estado', args=[plan.id]),
            {'estado': 'activo'},
        )
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'activo')

    def test_plan_delete(self):
        plan = self._make_plan()
        response = self.client.post(
            reverse('entrenamiento:plan_delete', args=[plan.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PlanRefuerzo.objects.filter(pk=plan.id).exists())


# ---------------------------------------------------------------------------
# 9. RolesTests (2 tests)
# ---------------------------------------------------------------------------
class RolesTests(BaseEntrenamientoTestCase):

    def test_no_autenticado_redirige_login(self):
        self.client.logout()
        response = self.client.get(reverse('entrenamiento:inicio'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_rol_estudiante_no_accede(self):
        est_user = Usuario.objects.create_user(
            username='est_noacceso', email='est_no@test.com', password='Clave123A!',
        )
        est_user.rol = 'estudiante'
        est_user.save()
        self.client.force_login(est_user)
        session = self.client.session
        session['centro_id'] = self.centro.id
        session.save()
        response = self.client.get(reverse('entrenamiento:inicio'))
        self.assertIn(response.status_code, [302, 403])


# ---------------------------------------------------------------------------
# 10. SesionTests (4 tests)
# ---------------------------------------------------------------------------
class SesionTests(BaseEntrenamientoTestCase):

    def test_sesion_list_renders(self):
        response = self.client.get(reverse('entrenamiento:sesion_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sesiones de Entrenamiento')

    def test_sesion_create(self):
        response = self.client.post(reverse('entrenamiento:sesion_create'), {
            'estudiante': self.estudiante.id,
            'anio_escolar': self.anio.id,
            'unidad': self.unidad.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SesionEntrenamiento.objects.filter(
                estudiante=self.estudiante,
            ).exists()
        )

    def test_sesion_detail_renders(self):
        sesion = self._make_sesion()
        response = self.client.get(
            reverse('entrenamiento:sesion_detail', args=[sesion.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')

    def test_sesion_delete(self):
        sesion = self._make_sesion()
        response = self.client.post(
            reverse('entrenamiento:sesion_delete', args=[sesion.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SesionEntrenamiento.objects.filter(pk=sesion.id).exists())


# ---------------------------------------------------------------------------
# 11. TramoCRUDTests (4 tests)
# ---------------------------------------------------------------------------
class TramoCRUDTests(BaseEntrenamientoTestCase):

    def test_tramo_list_renders(self):
        response = self.client.get(reverse('entrenamiento:tramo_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tramos de Edad')

    def test_tramo_create(self):
        response = self.client.post(reverse('entrenamiento:tramo_create'), {
            'nombre': 'Tramo 10-12',
            'edad_min': 10,
            'edad_max': 12,
            'orden': 2,
            'activo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TramoEdad.objects.filter(nombre='Tramo 10-12').exists()
        )

    def test_tramo_update(self):
        response = self.client.post(
            reverse('entrenamiento:tramo_update', args=[self.tramo.id]),
            {
                'nombre': 'Tramo 7-9 Actualizado',
                'edad_min': 7,
                'edad_max': 9,
                'orden': 1,
                'activo': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.tramo.refresh_from_db()
        self.assertEqual(self.tramo.nombre, 'Tramo 7-9 Actualizado')

    def test_tramo_delete(self):
        response = self.client.post(
            reverse('entrenamiento:tramo_delete', args=[self.tramo.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TramoEdad.objects.filter(pk=self.tramo.id).exists())


# ---------------------------------------------------------------------------
# 12. UnidadCRUDTests (3 tests)
# ---------------------------------------------------------------------------
class UnidadCRUDTests(BaseEntrenamientoTestCase):

    def test_unidad_list_renders(self):
        response = self.client.get(reverse('entrenamiento:unidad_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unidades de Entrenamiento')

    def test_unidad_create(self):
        response = self.client.post(reverse('entrenamiento:unidad_create'), {
            'tramo': self.tramo.id,
            'numero': 2,
            'nombre': 'Unidad B',
            'destrezas': [self.destreza.id],
            'activo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UnidadEntrenamiento.objects.filter(nombre='Unidad B').exists()
        )

    def test_unidad_delete(self):
        response = self.client.post(
            reverse('entrenamiento:unidad_delete', args=[self.unidad.id]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(UnidadEntrenamiento.objects.filter(pk=self.unidad.id).exists())
