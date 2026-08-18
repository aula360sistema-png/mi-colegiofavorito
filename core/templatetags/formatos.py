from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _formatear(valor, decimales):
    if valor is None or valor == '':
        valor = 0
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return '0.00' if decimales else '0'
    return f"{numero:,.{decimales}f}"


@register.filter
def dop(valor):
    return _formatear(valor, 2)


@register.filter
def dop0(valor):
    return _formatear(valor, 0)


@register.filter
def get_item(diccionario, clave):
    if not diccionario:
        return None
    return diccionario.get(clave)


def _iniciales(objeto):
    if not objeto:
        return '?'

    if hasattr(objeto, 'primer_nombre'):
        nombre = getattr(objeto, 'primer_nombre', '') or ''
        apellido = getattr(objeto, 'primer_apellido', '') or ''
        return f"{nombre[:1]}{apellido[:1]}".upper() or '?'
    else:
        nombre = getattr(objeto, 'first_name', '') or ''
        apellido = getattr(objeto, 'last_name', '') or ''
        return f"{nombre[:1]}{apellido[:1]}".upper() or '?'


@register.inclusion_tag('core/_avatar.html')
def avatar(objeto, size='w-9 h-9', color='from-blue-500 to-indigo-600', texto='text-xs', extra=''):
    return {
        'avatar_obj': objeto,
        'avatar_iniciales': _iniciales(objeto),
        'avatar_size': size,
        'avatar_color': color,
        'avatar_texto': texto,
        'avatar_extra': extra,
    }
