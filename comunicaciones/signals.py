from django.db.models.signals import post_save


def notificar_pago_creado(sender, instance, created, **kwargs):
    """Envía la notificación de pago a los tutores cuando se registra un pago.

    Solo se dispara en la creación; al editar un pago existente no se
    re-notifica. La notificación nunca debe romper el registro de la caja,
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


def conectar_signals():
    from django.apps import apps

    Pago = apps.get_model('caja', 'Pago')

    post_save.connect(
        notificar_pago_creado,
        sender=Pago,
        dispatch_uid='comunicaciones.pago.save',
    )
