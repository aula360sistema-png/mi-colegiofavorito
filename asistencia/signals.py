from django.db.models.signals import post_save, post_delete

from .models import AsistenciaEstudiante, DiaNoDocencia


def _centro_id_de(instance):
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id is not None:
        return centro_id

    # AsistenciaEstudiante: el centro se resuelve a través de la inscripción.
    inscripcion = getattr(instance, 'inscripcion', None)
    if inscripcion is not None:
        try:
            return inscripcion.centro_id
        except Exception:
            return None

    return None


def _invalidar(sender, instance, **kwargs):
    from .services import invalidar_asistencia_centro

    centro_id = _centro_id_de(instance)
    if centro_id:
        invalidar_asistencia_centro(centro_id)


def conectar_signals():
    for modelo in (AsistenciaEstudiante, DiaNoDocencia):
        post_save.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'asistencia.{modelo.__name__}.save',
        )
        post_delete.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'asistencia.{modelo.__name__}.delete',
        )
