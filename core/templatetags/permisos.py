from django import template
from django.core.cache import cache

register = template.Library()


@register.simple_tag(takes_context=True)
def has_perm_page(context, url_name):
    """Verifica si el usuario actual tiene permiso para acceder a una página.

    Uso en templates:
        {% has_perm_page 'estudiante_list' as puede_ver %}
        {% if puede_ver %}...{% endif %}
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False

    user = request.user

    if user.is_superuser:
        return True

    cache_key = f'perm_page:{url_name}'
    permiso = cache.get(cache_key)

    if permiso is None:
        from core.models import PermisoPagina
        permiso = PermisoPagina.objects.filter(
            url_name=url_name,
            activo=True,
        ).first()
        cache.set(cache_key, permiso, 300)

    if permiso is None:
        return True

    if permiso.roles_permitidos.filter(nombre=user.rol).exists():
        return True

    if permiso.usuarios_permitidos.filter(pk=user.pk).exists():
        return True

    return False
