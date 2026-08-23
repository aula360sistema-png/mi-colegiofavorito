from django import template
from django.core.cache import cache

register = template.Library()


def _obtener_permiso(request, url_name):
    """Devuelve el PermisoPagina activo para una URL (memoizado por request)."""
    if not hasattr(request, '_perm_page_cache'):
        request._perm_page_cache = {}

    if url_name in request._perm_page_cache:
        return request._perm_page_cache[url_name]

    cache_key = f'perm_page:{url_name}'
    permiso = cache.get(cache_key)

    if permiso is None:
        from core.models import PermisoPagina
        permiso = PermisoPagina.objects.filter(
            url_name=url_name,
            activo=True,
        ).first()
        cache.set(cache_key, permiso, 300)

    request._perm_page_cache[url_name] = permiso
    return permiso


def _resultado_usuario(request, url_name):
    """Resultado final para el usuario actual, memoizado por request.

    Evita las 2 consultas M2M (roles + usuarios) en cada aparición del
    enlace dentro de la misma página.
    """
    if not hasattr(request, '_perm_page_resultados'):
        request._perm_page_resultados = {}

    clave = f'u{request.user.pk}:{url_name}'
    if clave not in request._perm_page_resultados:
        user = request.user
        permiso = _obtener_permiso(request, url_name)

        if permiso is None:
            resultado = True
        elif permiso.roles_permitidos.filter(nombre=user.rol).exists():
            resultado = True
        else:
            resultado = permiso.usuarios_permitidos.filter(pk=user.pk).exists()

        request._perm_page_resultados[clave] = resultado

    return request._perm_page_resultados[clave]


@register.simple_tag(takes_context=True)
def has_perm_page(context, url_name):
    """Verifica si el usuario actual tiene permiso para acceder a una página.

    Uso en templates:
        {% has_perm_page 'estudiante_list' as puede_ver %}
        {% if puede_ver %}...{% endif %}

    Si no existe un registro activo para la URL, la página queda abierta.
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False

    if request.user.is_superuser:
        return True

    return _resultado_usuario(request, url_name)
