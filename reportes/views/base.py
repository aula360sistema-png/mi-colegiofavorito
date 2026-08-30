"""Helpers compartidos por las vistas de reportes (alcance por rol)."""

from django.db.models import Q

from academico.models import Grado, Seccion
from core.utils.anio import obtener_anio_activo

from reportes.services.base import es_rol_gestion, secciones_permitidas


def graduados_visibles(centro, anio, user):
    """Grados que el usuario puede consultar en reportes."""
    qs = Grado.objects.filter(secciones__centro=centro).distinct().order_by('orden')
    permitidas = secciones_permitidas(centro, anio, user)
    if permitidas is None:
        return qs
    ids = set(permitidas.values_list('grado_id', flat=True))
    return qs.filter(pk__in=ids)


def secciones_de_grado(centro, grado_id, anio, user):
    """Secciones de un grado que el usuario puede consultar."""
    if not grado_id:
        return Seccion.objects.none()
    qs = Seccion.objects.filter(centro=centro, grados__id=grado_id)
    permitidas = secciones_permitidas(centro, anio, user)
    if permitidas is None:
        return qs.order_by('nombre')
    ids = set(permitidas.filter(grado_id=grado_id).values_list('seccion_id', flat=True))
    return qs.filter(pk__in=ids).order_by('nombre')


def _q_inscripciones_permitidas(centro, anio, user):
    """Q() para filtrar Inscripcion por el alcance del usuario (None = todo)."""
    if es_rol_gestion(user):
        return None
    permitidas = secciones_permitidas(centro, anio, user)
    q = None
    for dm in permitidas:
        parte = Q(grado_id=dm.grado_id, seccion_id=dm.seccion_id)
        q = parte if q is None else (q | parte)
    return q if q is not None else Q(pk__in=[])


def inscripciones_visibles(centro, anio, user, grado_id='', seccion_id='', matricula=None):
    """Inscripciones que el usuario puede ver, ya resueltas en lista.

    Nombres de filtros admitidos: grado_id, seccion_id (ids string/digits),
    matricula (instancia de académico Grado/Seccion/Materia compatible).
    """
    from estudiantes.models import Inscripcion

    filtros = {'centro': centro, 'anio_escolar': anio}

    def _num(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    if matricula is not None:
        grado_id = matricula.grado_id
        seccion_id = matricula.seccion_id

    if grado_id:
        filtros['grado_id'] = _num(grado_id)
    if seccion_id:
        filtros['seccion_id'] = _num(seccion_id)

    qs = Inscripcion.objects.filter(**filtros)

    q = _q_inscripciones_permitidas(centro, anio, user)
    if q is not None:
        qs = qs.filter(q)

    return list(
        qs
        .select_related('estudiante', 'grado', 'seccion', 'anio_escolar')
        .order_by(
            'seccion__nombre',
            'estudiante__primer_apellido',
            'estudiante__primer_nombre',
        )
    )


def estudiantes_visibles(centro, anio, user):
    """Estudiantes que el usuario puede consultar en los filtros."""
    from estudiantes.models import Estudiante, Inscripcion

    qs = Estudiante.objects.filter(centro=centro).order_by(
        'primer_apellido', 'primer_nombre'
    )
    q = _q_inscripciones_permitidas(centro, anio, user)
    if q is not None:
        qs = qs.filter(
            pk__in=Inscripcion.objects.filter(centro=centro, anio_escolar=anio)
            .filter(q)
            .values('estudiante_id')
        )
    return qs


def contexto_base(centro, anio_actual=None):
    """Datos comunes de filtros: años y grados."""
    from core.models import AnioEscolar

    anios = AnioEscolar.objects.filter(centro=centro).order_by('-fecha_inicio')
    if anio_actual is None:
        anio_actual = obtener_anio_activo(centro)
    return anios, anio_actual