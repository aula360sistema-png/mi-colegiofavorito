from django.db.models.signals import post_save, post_delete

from core.cache_utils import invalidar_dominio


def invalidar_personal(sender, instance, **kwargs):
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_dominio(f'personal:{centro_id}')


def invalidar_actas(sender, instance, **kwargs):
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_dominio(f'actas:{centro_id}')


def conectar_signals():
    from .models import Acta, Administrativo

    post_save.connect(
        invalidar_personal,
        sender=Administrativo,
        dispatch_uid='administracion.administrativo.save',
    )
    post_delete.connect(
        invalidar_personal,
        sender=Administrativo,
        dispatch_uid='administracion.administrativo.delete',
    )
    post_save.connect(
        invalidar_actas,
        sender=Acta,
        dispatch_uid='administracion.acta.save',
    )
    post_delete.connect(
        invalidar_actas,
        sender=Acta,
        dispatch_uid='administracion.acta.delete',
    )
