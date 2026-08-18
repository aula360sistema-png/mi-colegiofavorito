"""Servicios con caché de core (dominio global `centros`)."""

from core.cache_utils import invalidar_dominio, obtener_o_generar, obtener_version, ttl
from core.models import CentroEducativo

TTL_CENTROS = 'CACHE_TTL_MEDIO'


def invalidar_centros():
    """Invalida el listado global de centros."""
    invalidar_dominio('centros')


def centros_listado():
    """Todos los centros ordenados por nombre (cacheado)."""
    clave = f'centros_lista:{obtener_version("centros")}'
    return obtener_o_generar(
        clave,
        lambda: list(CentroEducativo.objects.all().order_by('nombre')),
        version=1,
        timeout=ttl(TTL_CENTROS),
    )
