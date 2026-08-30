"""Utilidades base para las consultas de reportes."""

from academico.models import DocenteMateria, Grado, Seccion
from core.models import AnioEscolar
from core.utils.anio import obtener_anio_activo

ROLES_GESTION = ('director', 'secretaria', 'admin', 'superadmin')


def anio_de(centro, anio_id):
    """Devuelve el año escolar solicitado (o el activo) del centro."""
    if anio_id:
        try:
            anio_id = int(anio_id)
        except (TypeError, ValueError):
            anio_id = None
        if anio_id:
            anio = AnioEscolar.objects.filter(pk=anio_id, centro=centro).first()
            if anio:
                return anio
    return obtener_anio_activo(centro)


def es_rol_gestion(user):
    """True para roles con acceso total a los reportes del centro."""
    return user.rol in ROLES_GESTION


def docente_de(user, centro):
    """El registro Docente vinculado al usuario, si el rol es 'docente'."""
    if user.rol != 'docente':
        return None
    from docentes.models import Docente
    return Docente.objects.filter(centro=centro, usuario=user).first()


def secciones_permitidas(centro, anio, user):
    """Restricción por rol de los reportes.

    Devuelve None si el usuario ve todo el centro (roles de gestión) o un
    queryset de DocenteMateria con las asignaciones del docente en el año
    (no aplica para otros roles: queryset vacío, nada permitido).
    """
    if es_rol_gestion(user):
        return None
    docente = docente_de(user, centro)
    if not anio or not docente:
        return DocenteMateria.objects.none()
    return DocenteMateria.objects.filter(
        docente=docente,
        anio_escolar=anio,
    ).select_related('grado', 'seccion')