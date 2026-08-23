"""Servicios con caché de core (dominio global `centros`)."""

from core.cache_utils import invalidar_dominio, obtener_o_generar, obtener_version, ttl
from core.models import CentroEducativo

TTL_CENTROS = 'CACHE_TTL_MEDIO'

# Mapa canónico: clave lógica de módulo -> flag en ConfiguracionCentro.
# Toda consulta de "¿este módulo está contratado/activo?" debe pasar por
# modulo_activo(); ningún flujo debe asumir la presencia de otro módulo.
FLAGS_MODULOS = {
    'asistencia': 'modulo_asistencia',
    'caja': 'modulo_caja',
    'nomina': 'modulo_nomina',
    'biblioteca': 'modulo_biblioteca',
    'transporte': 'modulo_transporte',
    'cafeteria': 'modulo_cafeteria',
    'inventario': 'modulo_inventario',
    'reportes': 'modulo_reportes',
    'mensajeria': 'modulo_mensajeria',
    'certificados': 'modulo_certificados',
    'facturacion': 'permitir_facturacion',
    'pago_online': 'permitir_pago_online',
}


def modulo_activo(centro_id, nombre):
    """True si el módulo ``nombre`` está activo para el centro dado.

    ``centro_id`` puede ser un id o una instancia de centro. Usa la
    configuración cacheada del centro (se invalida al guardar).
    """
    from core.context_processors import obtener_configuracion_centro

    if isinstance(centro_id, CentroEducativo):
        centro_id = centro_id.id
    if not centro_id:
        return False

    flag = FLAGS_MODULOS.get(nombre)
    if not flag:
        return False

    configuracion = obtener_configuracion_centro(centro_id)
    return bool(configuracion and getattr(configuracion, flag, False))


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
