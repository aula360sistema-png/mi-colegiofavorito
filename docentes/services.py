"""Caché de listados y panel del docente (dominio `docentes:{centro}`).

El listado de docentes y el panel del docente se consultan en cada request.
Aquí se cachean los datos base por centro y las vistas filtran en memoria.

Estrategia idéntica a caja/nómina: cuando cambia Docente, DocenteMateria,
Acta, Inscripcion o PeriodoAnio se incrementa la versión del dominio y las
claves viejas quedan huérfanas.
"""

from core.cache_utils import (
    invalidar_dominio,
    obtener_o_generar,
    obtener_version,
    ttl,
)
from docentes.models import Docente

TTL_DOCENTES = 'CACHE_TTL_MEDIO'


def invalidar_docentes_centro(centro_id):
    """Invalida el listado y los paneles de docentes de un centro."""
    invalidar_dominio(f'docentes:{centro_id}')


def _version_docentes(centro_id):
    return obtener_version(f'docentes:{centro_id}')


def docentes_del_centro(centro):
    """Todos los docentes del centro (cacheados). La vista filtra en memoria."""
    clave = f'docentes_lista:{centro.id}:{_version_docentes(centro.id)}'
    return obtener_o_generar(
        clave,
        lambda: list(
            Docente.objects.filter(centro=centro).order_by(
                'primer_apellido', 'primer_nombre'
            )
        ),
        version=1,
        timeout=ttl(TTL_DOCENTES),
    )


def datos_dashboard_docente(docente, anio):
    """Datos del panel del docente cacheados por dominio del centro."""
    clave = (
        f'docente_dashboard:{docente.id}:{anio.id}:'
        f'{_version_docentes(docente.centro_id)}'
    )
    return obtener_o_generar(
        clave,
        lambda: _datos_dashboard_docente_sql(docente, anio),
        version=1,
        timeout=ttl(TTL_DOCENTES),
    )


def _datos_dashboard_docente_sql(docente, anio):
    from django.db.models import Count

    from academico.models import DocenteMateria
    from academico.services import estructura
    from administracion.models import Acta
    from estudiantes.models import Inscripcion

    asignaciones = list(
        DocenteMateria.objects.filter(
            docente=docente,
            anio_escolar=anio,
        ).select_related('asignatura', 'grado', 'seccion')
    )

    centro = docente.centro

    grado_ids = [a.grado_id for a in asignaciones]
    seccion_ids = [a.seccion_id for a in asignaciones]

    # Conteo de estudiantes por (grado, sección) del año, en una consulta.
    conteos = {}
    for gid, sid, total in (
        Inscripcion.objects.filter(
            anio_escolar=anio,
            grado_id__in=grado_ids,
            seccion_id__in=seccion_ids,
        )
        .values_list('grado_id', 'seccion_id')
        .annotate(total=Count('id'))
        .values_list('grado_id', 'seccion_id', 'total')
    ):
        conteos[(gid, sid)] = total

    # Actas del centro/año agrupadas por (grado, sección), en una consulta.
    actas_por_grupo = {}
    for acta in Acta.objects.filter(
        centro=centro,
        anio_escolar=anio,
        grado_id__in=grado_ids,
    ):
        actas_por_grupo.setdefault((acta.grado_id, acta.seccion), []).append(acta)

    asignaciones_con_notas = 0
    asignaciones_completas = 0
    total_estudiantes = 0
    lista = []

    for a in asignaciones:
        cantidad_estudiantes = conteos.get((a.grado_id, a.seccion_id), 0)

        actas = actas_por_grupo.get((a.grado_id, a.seccion.nombre), [])
        estado = 'pendiente'

        if actas:
            estado = 'progreso'
            completas = True

            for acta in actas:
                datos = acta.datos or {}
                asignaturas = datos.get('asignaturas', [])
                pfs = [
                    x.get('pf')
                    for x in asignaturas
                    if x.get('pf') is not None
                ]
                if not asignaturas or len(pfs) != len(asignaturas):
                    completas = False
                    break

            if completas:
                estado = 'completo'
            if estado in ('progreso', 'completo'):
                asignaciones_con_notas += 1
            if estado == 'completo':
                asignaciones_completas += 1

        lista.append({
            'obj': a,
            'estado': estado,
            'cantidad_estudiantes': cantidad_estudiantes,
        })
        total_estudiantes += cantidad_estudiantes

    # Períodos activos del año (catálogos ya cacheados de academico).
    estados = estructura.estados_periodo_anio(anio)
    ids_activos = {e.periodo_id for e in estados if e.activo}
    periodos = [p for p in estructura.periodos(centro) if p.id in ids_activos]

    return {
        'asignaciones': lista,
        'total_asignaciones': len(asignaciones),
        'asignaciones_con_notas': asignaciones_con_notas,
        'asignaciones_completas': asignaciones_completas,
        'total_estudiantes': total_estudiantes,
        'periodos': periodos,
        'grupos': _agrupar_por_grado_seccion(lista),
    }


def _agrupar_por_grado_seccion(lista):
    """Agrupa asignaciones por grado -> sección para el dashboard."""
    from collections import OrderedDict

    grados = OrderedDict()
    for item in lista:
        a = item['obj']
        grado_key = a.grado_id
        grado_nombre = a.grado.nombre
        seccion_nombre = a.seccion.nombre

        if grado_key not in grados:
            grados[grado_key] = {
                'grado_id': grado_key,
                'grado_nombre': grado_nombre,
                'secciones': OrderedDict(),
            }

        secc_key = a.seccion_id
        if secc_key not in grados[grado_key]['secciones']:
            grados[grado_key]['secciones'][secc_key] = {
                'seccion_nombre': seccion_nombre,
                'asignaciones': [],
            }

        grados[grado_key]['secciones'][secc_key]['asignaciones'].append(item)

    return list(grados.values())
