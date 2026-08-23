from django.db.models.signals import m2m_changed, post_save, post_delete

from .cache_utils import borrar, invalidar_dominio, ttl
from .models import AnioEscolar, CentroEducativo, ConfiguracionCentro, PermisoPagina


def invalidar_config_centro(sender, instance, **kwargs):
    if instance.centro_id:
        borrar(f'config:{instance.centro_id}')
        # El dashboard depende de flags de módulos (p. ej. caja_activa).
        invalidar_dominio(f'dashboard:{instance.centro_id}')


def invalidar_permiso_pagina(instance):
    borrar(f'perm_mw:{instance.url_name}')
    borrar(f'perm_page:{instance.url_name}')


def invalidar_m2m_permiso(sender, instance, **kwargs):
    # Cubre ediciones fuera del CRUD propio (ej. Django admin): los M2M se
    # guardan después del save del PermisoPagina y no disparan post_save.
    invalidar_permiso_pagina(instance)


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
    for campo in ('roles_permitidos', 'usuarios_permitidos'):
        m2m_changed.connect(
            invalidar_m2m_permiso,
            sender=PermisoPagina._meta.get_field(campo).remote_field.through,
            dispatch_uid=f'core.permisopagina_m2m_{campo}',
        )
