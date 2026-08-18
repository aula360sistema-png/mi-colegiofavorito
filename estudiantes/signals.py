from django.db.models.signals import post_save, post_delete

from estudiantes.services.kardex import (
    invalidar_kardex_estudiante,
    invalidar_kardex_estructura,
)
from estudiantes.services.listados import invalidar_estudiantes_centro


def _estudiante_de_inscripcion(inscripcion):
    return inscripcion.estudiante_id


def invalidar_por_calificacion(sender, instance, **kwargs):
    inscripcion_id = instance.inscripcion_id
    if inscripcion_id:
        from estudiantes.models import Inscripcion

        inscripcion = (
            Inscripcion.objects
            .filter(id=inscripcion_id)
            .values_list('estudiante_id', flat=True)
            .first()
        )
        if inscripcion:
            invalidar_kardex_estudiante(inscripcion)


def invalidar_por_inscripcion(sender, instance, **kwargs):
    from administracion.views import invalidar_dashboard
    if instance.centro_id:
        invalidar_dashboard(instance.centro_id)
        invalidar_estudiantes_centro(instance.centro_id)
    if instance.estudiante_id:
        invalidar_kardex_estudiante(instance.estudiante_id)


def invalidar_por_observacion(sender, instance, **kwargs):
    if instance.estudiante_id:
        invalidar_kardex_estudiante(instance.estudiante_id)

        from estudiantes.models import Estudiante

        centro_id = (
            Estudiante.objects
            .filter(id=instance.estudiante_id)
            .values_list('centro_id', flat=True)
            .first()
        )
        if centro_id:
            invalidar_estudiantes_centro(centro_id)


def invalidar_por_asistencia(sender, instance, **kwargs):
    if instance.inscripcion_id:
        from estudiantes.models import Inscripcion
        inscripcion = (
            Inscripcion.objects
            .filter(id=instance.inscripcion_id)
            .values_list('estudiante_id', flat=True)
            .first()
        )
        if inscripcion:
            invalidar_kardex_estudiante(inscripcion)


def invalidar_estructura_centro(sender, instance, **kwargs):
    """Cambios en periodos / asignaciones / estructura invalidan el kardex
    de todo el centro (las claves incluyen la versión de estructura)."""
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_kardex_estructura(centro_id)
        return

    # DocenteMateria: se resuelve el centro a través del anio_escolar.
    anio_id = getattr(instance, 'anio_escolar_id', None)
    if anio_id:
        from core.models import AnioEscolar
        centro_id = (
            AnioEscolar.objects
            .filter(id=anio_id)
            .values_list('centro_id', flat=True)
            .first()
        )
        if centro_id:
            invalidar_kardex_estructura(centro_id)


def invalidar_por_estudiante(sender, instance, **kwargs):
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_estudiantes_centro(centro_id)


def invalidar_por_solicitud(sender, instance, **kwargs):
    if instance.estudiante_id:
        from estudiantes.models import Estudiante

        centro_id = (
            Estudiante.objects
            .filter(id=instance.estudiante_id)
            .values_list('centro_id', flat=True)
            .first()
        )
        if centro_id:
            invalidar_estudiantes_centro(centro_id)


def conectar_signals():
    from academico.models import Calificacion, DocenteMateria, Periodo
    from asistencia.models import AsistenciaEstudiante
    from core.models import ConfiguracionCentro
    from estudiantes.models import (
        Estudiante,
        Inscripcion,
        ObservacionEstudiante,
        SolicitudCertificado,
    )

    # Datos del estudiante que alimentan el kardex
    post_save.connect(
        invalidar_por_calificacion,
        sender=Calificacion,
        dispatch_uid='kardex.calificacion.save',
    )
    post_delete.connect(
        invalidar_por_calificacion,
        sender=Calificacion,
        dispatch_uid='kardex.calificacion.delete',
    )
    post_save.connect(
        invalidar_por_inscripcion,
        sender=Inscripcion,
        dispatch_uid='kardex.inscripcion.save',
    )
    post_delete.connect(
        invalidar_por_inscripcion,
        sender=Inscripcion,
        dispatch_uid='kardex.inscripcion.delete',
    )
    post_save.connect(
        invalidar_por_observacion,
        sender=ObservacionEstudiante,
        dispatch_uid='kardex.observacion.save',
    )
    post_delete.connect(
        invalidar_por_observacion,
        sender=ObservacionEstudiante,
        dispatch_uid='kardex.observacion.delete',
    )
    post_save.connect(
        invalidar_por_asistencia,
        sender=AsistenciaEstudiante,
        dispatch_uid='kardex.asistencia.save',
    )
    post_delete.connect(
        invalidar_por_asistencia,
        sender=AsistenciaEstudiante,
        dispatch_uid='kardex.asistencia.delete',
    )

    # Estructura (afecta a todo el centro)
    for modelo in (Periodo, DocenteMateria):
        post_save.connect(
            invalidar_estructura_centro,
            sender=modelo,
            dispatch_uid=f'kardex.estructura.{modelo.__name__}.save',
        )
        post_delete.connect(
            invalidar_estructura_centro,
            sender=modelo,
            dispatch_uid=f'kardex.estructura.{modelo.__name__}.delete',
        )

    # Listas de estudiantes del centro
    post_save.connect(
        invalidar_por_estudiante,
        sender=Estudiante,
        dispatch_uid='listados.estudiante.save',
    )
    post_delete.connect(
        invalidar_por_estudiante,
        sender=Estudiante,
        dispatch_uid='listados.estudiante.delete',
    )

    # Solicitudes de certificados (alimentan el listado del admin)
    post_save.connect(
        invalidar_por_solicitud,
        sender=SolicitudCertificado,
        dispatch_uid='listados.solicitud.save',
    )
    post_delete.connect(
        invalidar_por_solicitud,
        sender=SolicitudCertificado,
        dispatch_uid='listados.solicitud.delete',
    )

    # Nota mínima: invalida el valor cacheado y el kardex del centro
    def invalidar_nota_minima(sender, instance, **kwargs):
        from core.cache_utils import borrar
        if instance.centro_id:
            borrar(f'nota_minima:{instance.centro_id}')
            invalidar_kardex_estructura(instance.centro_id)

    post_save.connect(
        invalidar_nota_minima,
        sender=ConfiguracionCentro,
        dispatch_uid='kardex.config.save',
    )
