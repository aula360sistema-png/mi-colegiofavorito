from administracion.models import AnioEscolar
from core.models import AnioEscolar


def obtener_anio_activo(centro, obligatorio=False):
    anio = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

    if obligatorio and not anio:
        raise ValueError("No hay año escolar activo")

    return anio