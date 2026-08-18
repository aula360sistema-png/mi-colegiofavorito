from django.db.models.signals import post_save, post_delete

from .models import (
    ConfiguracionNomina,
    DescuentoNomina,
    IngresoNomina,
    Nomina,
    PeriodoNomina,
)


def _invalidar(sender, instance, **kwargs):
    from .services import invalidar_nomina_centro

    centro_id = getattr(instance, 'centro_id', None)

    if centro_id is None:
        # Nomina: vía periodo. Ingreso/DescuentoNomina: vía nomina.
        periodo = getattr(instance, 'periodo', None)
        if periodo is not None:
            try:
                centro_id = periodo.centro_id
            except Exception:
                centro_id = None

        if centro_id is None:
            nomina = getattr(instance, 'nomina', None)
            if nomina is not None:
                try:
                    centro_id = nomina.periodo.centro_id
                except Exception:
                    centro_id = None

    if centro_id:
        invalidar_nomina_centro(centro_id)


def conectar_signals():
    for modelo in (
        ConfiguracionNomina,
        PeriodoNomina,
        Nomina,
        IngresoNomina,
        DescuentoNomina,
    ):
        post_save.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'nomina.{modelo.__name__}.save',
        )
        post_delete.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'nomina.{modelo.__name__}.delete',
        )
