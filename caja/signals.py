from django.db.models.signals import post_save, post_delete

from caja.models import (
    AsignacionConcepto,
    ConceptoPago,
    Egreso,
    Pago,
    SesionCaja,
)


def invalidar_dashboard_pago(sender, instance, **kwargs):
    from administracion.views import invalidar_dashboard
    from .services import invalidar_pagos_centro
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_dashboard(centro_id)
        invalidar_pagos_centro(centro_id)


def invalidar_dashboard_sesion(sender, instance, **kwargs):
    from administracion.views import invalidar_dashboard
    from .services import invalidar_pagos_centro
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_dashboard(centro_id)
        invalidar_pagos_centro(centro_id)


def invalidar_pagos(sender, instance, **kwargs):
    from .services import invalidar_pagos_centro
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id:
        invalidar_pagos_centro(centro_id)


def conectar_signals():
    post_save.connect(
        invalidar_dashboard_pago,
        sender=Pago,
        dispatch_uid='dashboard.pago.save',
    )
    post_delete.connect(
        invalidar_dashboard_pago,
        sender=Pago,
        dispatch_uid='dashboard.pago.delete',
    )
    post_save.connect(
        invalidar_dashboard_sesion,
        sender=SesionCaja,
        dispatch_uid='dashboard.sesion.save',
    )
    post_delete.connect(
        invalidar_dashboard_sesion,
        sender=SesionCaja,
        dispatch_uid='dashboard.sesion.delete',
    )
    # Movimientos de caja que alimentan balances/cuentas por cobrar
    for modelo in (Egreso, AsignacionConcepto, ConceptoPago):
        post_save.connect(
            invalidar_pagos,
            sender=modelo,
            dispatch_uid=f'pagos.{modelo.__name__}.save',
        )
        post_delete.connect(
            invalidar_pagos,
            sender=modelo,
            dispatch_uid=f'pagos.{modelo.__name__}.delete',
        )
