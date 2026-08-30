"""Validadores de formato para República Dominicana (cédula y teléfono)."""

import re


def solo_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def es_cedula_rd(valor):
    """Cédula dominicana: 11 dígitos (000-0000000-0)."""
    return len(solo_digitos(valor)) == 11


def es_telefono_rd(valor):
    """Teléfono de RD: 10 dígitos (000-000-0000)."""
    return len(solo_digitos(valor)) == 10