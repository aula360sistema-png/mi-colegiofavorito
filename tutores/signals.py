from django.db.models.signals import m2m_changed, post_save, post_delete

from .models import Tutor


def _centro_id_de(instance):
    return getattr(instance, 'centro_id', None)


def _invalidar(sender, instance, **kwargs):
    from .services import invalidar_tutores_centro

    centro_id = _centro_id_de(instance)
    if centro_id:
        invalidar_tutores_centro(centro_id)


def _invalidar_m2m(sender, instance, action, reverse, pk_set, **kwargs):
    from .services import invalidar_tutores_centro

    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    if reverse:
        ids = pk_set or ()
        for pk in ids:
            try:
                invalidar_tutores_centro(
                    Tutor.objects.values_list('centro_id', flat=True).get(pk=pk)
                )
            except Tutor.DoesNotExist:
                pass
        return

    centro_id = _centro_id_de(instance)
    if centro_id:
        invalidar_tutores_centro(centro_id)


def conectar_signals():
    from estudiantes.models import Estudiante, Inscripcion

    for modelo in (Tutor, Inscripcion, Estudiante):
        post_save.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'tutores.{modelo.__name__}.save',
        )
        post_delete.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'tutores.{modelo.__name__}.delete',
        )

    m2m_changed.connect(
        _invalidar_m2m,
        sender=Tutor.estudiantes.through,
        dispatch_uid='tutores.estudiantes.m2m',
    )
