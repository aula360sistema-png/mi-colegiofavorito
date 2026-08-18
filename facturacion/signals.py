from django.db.models.signals import post_save, post_delete

from facturacion.models import Factura


def invalidar_facturas(sender, instance, **kwargs):
    from .services import invalidar_facturas_centro
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_facturas_centro(centro_id)


def conectar_signals():
    post_save.connect(
        invalidar_facturas,
        sender=Factura,
        dispatch_uid='facturas.factura.save',
    )
    post_delete.connect(
        invalidar_facturas,
        sender=Factura,
        dispatch_uid='facturas.factura.delete',
    )
