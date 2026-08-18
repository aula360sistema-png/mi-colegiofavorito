from academico.models import Periodo, PeriodoAnio
from core.models import AnioEscolar


def sincronizar_periodos_anio(anio_escolar):
    """Crea los PeriodoAnio faltantes para un año escolar dado."""
    creados = 0
    for periodo in Periodo.objects.filter(centro=anio_escolar.centro):
        _, creado = PeriodoAnio.objects.get_or_create(
            periodo=periodo,
            anio_escolar=anio_escolar,
            defaults={
                'activo': anio_escolar.activo,
                'cerrado': not anio_escolar.activo,
            }
        )
        if creado:
            creados += 1
    return creados


def abrir_periodos_anio(anio_escolar):
    """Sincroniza y deja abiertos los períodos del año activo.

    Si el año es activo, sus períodos se abren (activo=True, cerrado=False)
    y los de los demás años del centro se cierran.
    """
    from .estructura import invalidar_estructura

    sincronizar_periodos_anio(anio_escolar)

    if not anio_escolar.activo:
        return

    PeriodoAnio.objects.filter(anio_escolar=anio_escolar).update(
        activo=True,
        cerrado=False,
        fecha_cierre=None,
    )
    PeriodoAnio.objects.filter(
        anio_escolar__centro=anio_escolar.centro
    ).exclude(anio_escolar=anio_escolar).update(
        activo=False,
        cerrado=True,
    )

    # Los .update() masivos no disparan post_save: invalidar aquí.
    invalidar_estructura(anio_escolar.centro_id)


def sincronizar_periodos_centro(centro):
    """Crea los PeriodoAnio faltantes para todos los años del centro."""
    creados = 0
    for anio in AnioEscolar.objects.filter(centro=centro):
        creados += sincronizar_periodos_anio(anio)
    return creados
