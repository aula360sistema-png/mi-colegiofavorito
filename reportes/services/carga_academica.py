"""Servicio de carga académica (asignaciones docente -> grado/sección)."""

from collections import defaultdict

from academico.models import DocenteMateria
from docentes.models import Docente

from reportes.services.base import anio_de, es_rol_gestion


def carga_academica(centro, anio_id='', grado_id='', docente_id='', user=None):
    """Asignaciones de docentes (DocenteMateria) filtradas por centro.

    Devuelve (anio, filas) donde cada fila es {docente, asignaciones}.
    Los docentes activos sin asignaciones aparecen con lista vacía.

    Si el usuario es un docente, solo ve su propia carga académica.
    """
    anio = anio_de(centro, anio_id)
    if not anio:
        return None, []

    qs = (
        DocenteMateria.objects
        .filter(anio_escolar=anio, docente__centro=centro)
        .select_related('docente', 'asignatura', 'grado', 'seccion')
    )

    docentes = Docente.objects.filter(centro=centro)

    if user is not None and not es_rol_gestion(user):
        from reportes.services.base import docente_de
        docente = docente_de(user, centro)
        if not docente:
            return anio, []
        docentes = docentes.filter(pk=docente.pk)
        qs = qs.filter(docente=docente)
    elif docente_id.isdigit():
        docentes = docentes.filter(pk=docente_id)

    if grado_id.isdigit():
        qs = qs.filter(grado_id=grado_id)

    asignaciones = list(
        qs.order_by(
            'docente__primer_apellido',
            'docente__primer_nombre',
            'grado__orden',
            'seccion__nombre',
            'asignatura__nombre',
        )
    )

    if user is None or es_rol_gestion(user):
        if not docente_id.isdigit():
            docentes = docentes.filter(estado='activo')
    docentes = docentes.order_by('primer_apellido', 'primer_nombre')

    por_docente = defaultdict(list)
    for a in asignaciones:
        por_docente[a.docente_id].append(a)

    filas = [
        {'docente': d, 'asignaciones': por_docente.get(d.id, [])}
        for d in docentes
    ]
    return anio, filas