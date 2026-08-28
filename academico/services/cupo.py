"""Control de cupo por sección.

Helper centralizado para validar la capacidad de una sección antes de
matricular o reubicar estudiantes. Todos los puntos de entrada que
inscriben gente en una sección deben pasar por aquí para no repetir
lógica con criterios ligeramente distintos en cada lugar.
"""

from django.db.models import Count

from estudiantes.models import Inscripcion


def cantidad_ocupada(seccion, grado, anio):
    """Cuenta estudiantes ya matriculados en la sección ese año y grado."""
    qs = Inscripcion.objects.filter(
        seccion=seccion,
        grado=grado,
        anio_escolar=anio,
    )
    # Los retirados no consumen cupo.
    try:
        qs = qs.exclude(estado_final='retirado')
    except Exception:
        pass
    return qs.aggregate(total=Count('id'))['total'] or 0


def hay_cupo_disponible(seccion, grado, anio, excluir_inscripcion_id=None):
    """True si la sección aún admite al estudiante según su capacidad.

    - Si la sección no tiene capacidad (None) siempre devuelve True.
    - ``excluir_inscripcion_id`` permite revalidar sin contar la
      inscripción que se está moviendo (cambio de sección).
    """
    if seccion.capacidad_max is None:
        return True

    qs = Inscripcion.objects.filter(
        seccion=seccion,
        grado=grado,
        anio_escolar=anio,
    )
    if excluir_inscripcion_id is not None:
        qs = qs.exclude(pk=excluir_inscripcion_id)

    ocupados = qs.aggregate(total=Count('id'))['total'] or 0
    return ocupados < seccion.capacidad_max


def cupo_disponible_de(seccion, grado, anio):
    """Cupo restante (int) de una sección para el grado/año.

    Devuelve None si la sección no tiene límite.
    """
    if seccion.capacidad_max is None:
        return None
    ocupados = cantidad_ocupada(seccion, grado, anio)
    return max(seccion.capacidad_max - ocupados, 0)
