from django.db.models.signals import post_save, post_delete

from .cache_utils import borrar, invalidar_dominio, ttl
from .models import AnioEscolar, CentroEducativo, ConfiguracionCentro


def invalidar_config_centro(sender, instance, **kwargs):
    if instance.centro_id:
        borrar(f'config:{instance.centro_id}')


def invalidar_estructura_anio(sender, instance, **kwargs):
    # AnioEscolar alimenta los catálogos de estructura académica
    # (anio_escolar_list, docentemateria, horario, período↔año).
    if instance.centro_id:
        invalidar_dominio(f'estructura:{instance.centro_id}')


def invalidar_listado_centros(sender, instance, **kwargs):
    from .services import invalidar_centros

    invalidar_centros()


def conectar_signals():
    post_save.connect(
        invalidar_config_centro,
        sender=ConfiguracionCentro,
        dispatch_uid='core.config_post_save',
    )
    post_delete.connect(
        invalidar_config_centro,
        sender=ConfiguracionCentro,
        dispatch_uid='core.config_post_delete',
    )
    post_save.connect(
        invalidar_estructura_anio,
        sender=AnioEscolar,
        dispatch_uid='core.anioescolar_post_save',
    )
    post_delete.connect(
        invalidar_estructura_anio,
        sender=AnioEscolar,
        dispatch_uid='core.anioescolar_post_delete',
    )
    post_save.connect(
        invalidar_listado_centros,
        sender=CentroEducativo,
        dispatch_uid='core.centroeducativo_post_save',
    )
    post_delete.connect(
        invalidar_listado_centros,
        sender=CentroEducativo,
        dispatch_uid='core.centroeducativo_post_delete',
    )
