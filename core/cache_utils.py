"""Utilidades de caché para los datos más consultados del sistema.

Estrategia de invalidación:
  - Los valores se guardan con una "versión" por dominio (ej. un estudiante).
  - Cuando cambia el dominio (se guardan calificaciones, inscripciones, etc.)
    se incrementa la versión con `invalidar_dominio()`, lo que invalida
    todas las claves de ese dominio de forma inmediata.
"""

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('security')

TTL_CORTO = 'CACHE_TTL_CORTO'
TTL_MEDIO = 'CACHE_TTL_MEDIO'
TTL_LARGO = 'CACHE_TTL_LARGO'


def ttl(nombre=TTL_MEDIO, default=None):
    return getattr(settings, nombre, default or 300)


def _clave_version(dominio):
    return f'version:{dominio}'


def obtener_version(dominio):
    return cache.get_or_set(_clave_version(dominio), 1, timeout=ttl(TTL_LARGO))


def invalidar_dominio(dominio):
    """Incrementa la versión del dominio. Las claves viejas quedan huérfanas."""
    try:
        cache.incr(_clave_version(dominio))
    except ValueError:
        cache.set(_clave_version(dominio), 2, timeout=ttl(TTL_LARGO))


def obtener_o_generar(clave, generador, version, timeout=None):
    """Devuelve el valor cacheado o ejecuta `generador` y lo guarda."""
    v = version
    valor = cache.get(clave, version=v)
    if valor is not None:
        return valor
    valor = generador()
    cache.set(clave, valor, timeout=timeout, version=v)
    return valor


def borrar(clave, version=None):
    cache.delete(clave, version=version)
