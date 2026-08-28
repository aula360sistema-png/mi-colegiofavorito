"""Servicios de inscripciones: movimiento entre secciones."""

from auditoria.services import registrar_evento


class CambiarSeccionError(Exception):
    """No se puede mover la inscripción a la sección pedida."""


def cambiar_seccion(inscripcion, seccion, usuario):
    """Mueve una inscripción a otra sección del mismo grado.

    Valida centro y que el grado use la sección destino; deja constancia
    en la bitácora de auditoría. Devuelve (seccion_anterior, seccion_nueva).
    """
    if seccion.centro_id != inscripcion.centro_id:
        raise CambiarSeccionError('La sección pertenece a otro centro.')

    if seccion.pk == inscripcion.seccion_id:
        raise CambiarSeccionError(
            'El estudiante ya está inscrito en esa sección.'
        )

    if not inscripcion.grado.secciones.filter(pk=seccion.pk).exists():
        raise CambiarSeccionError(
            f'La sección {seccion.nombre} no está disponible para el '
            f'{inscripcion.grado.nombre}.'
        )

    from .cupo import hay_cupo_disponible

    if not hay_cupo_disponible(
        seccion,
        inscripcion.grado,
        inscripcion.anio_escolar,
        excluir_inscripcion_id=inscripcion.id,
    ):
        raise CambiarSeccionError(
            f'La sección {seccion.nombre} está llena.'
        )

    anterior = inscripcion.seccion
    inscripcion.seccion = seccion
    inscripcion.save(update_fields=['seccion'])

    registrar_evento(
        accion='EDITAR',
        descripcion=(
            f"Cambio de sección: {inscripcion.estudiante.nombre_completo()} "
            f"({inscripcion.grado.nombre}) pasó de {anterior.nombre} a "
            f"{seccion.nombre} ({inscripcion.anio_escolar.nombre})."
        ),
        usuario=usuario,
        modulo='ACADEMICO',
        modelo='Inscripcion',
        objeto_id=inscripcion.id,
        riesgo='BAJO',
        datos_anteriores={'seccion': anterior.nombre},
        datos_nuevos={'seccion': seccion.nombre},
    )

    return anterior, seccion
