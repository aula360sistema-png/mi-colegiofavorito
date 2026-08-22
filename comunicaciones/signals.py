from django.db.models.signals import post_delete, post_save


def notificar_pago_creado(sender, instance, created, **kwargs):
    """Envia la notificacion de pago a los tutores cuando se registra un pago.

    Solo se dispara en la creacion; al editar un pago existente no se
    re-notifica. La notificacion nunca debe romper el registro de la caja,
    por eso el servicio captura y registra los errores.
    """
    if not created:
        return

    try:
        from .services import notificar_pago

        notificar_pago(instance)
    except Exception:  # noqa: BLE001 - la caja no debe fallar por esto
        import logging

        logging.getLogger('comunicaciones').exception(
            'Error al notificar el pago %s',
            instance.recibo or instance.id,
        )


def comunicado_guardado(sender, instance, **kwargs):
    """Invalida el cache de comunicados del centro al crear/editar/borrar."""
    from comunicaciones.services.comunicados import invalidar_comunicados

    invalidar_comunicados(instance.centro_id)


def conectar_signals():
    from django.apps import apps

    Pago = apps.get_model('caja', 'Pago')

    post_save.connect(
        notificar_pago_creado,
        sender=Pago,
        dispatch_uid='comunicaciones.pago.save',
    )

    Comunicado = apps.get_model('comunicaciones', 'Comunicado')

    post_save.connect(
        comunicado_guardado,
        sender=Comunicado,
        dispatch_uid='comunicaciones.comunicado.save',
    )
    post_delete.connect(
        comunicado_guardado,
        sender=Comunicado,
        dispatch_uid='comunicaciones.comunicado.delete',
    )
