import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


class SecurityHeadersMiddleware:
    """Agrega cabeceras de seguridad que Django no genera por defecto."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        return response


class AdminBruteForceMiddleware:
    """Bloquea fuerza bruta sobre el login de Django admin."""

    MAX_FALLOS = 10

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == 'POST'
            and request.path.startswith('/admin/login/')
            and not request.user.is_authenticated
        ):
            ip = request.META.get('REMOTE_ADDR', '?')
            if response.status_code == 200:
                clave = f"admin_fallos:{ip}"
                fallos = cache.get(clave, 0) + 1
                cache.set(clave, fallos, 15 * 60)
                if fallos >= self.MAX_FALLOS:
                    return HttpResponseForbidden('Demasiados intentos. Panel bloqueado temporalmente.')
            else:
                cache.delete(f"admin_fallos:{ip}")
        return response


class IdleTimeoutMiddleware:
    """Cierra la sesión tras un periodo de inactividad.

    Solo actualiza la marca de actividad si pasó al menos un minuto, para
    evitar escribir la sesión (caché + BD) en cada request.
    """

    MIN_INTERVALO = 60  # segundos entre escrituras de actividad

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = (
            '/usuarios/login/',
            '/usuarios/verificar-2fa/',
            '/usuarios/configurar-2fa/',
            '/admin/',
            '/media/',
        )

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.path.startswith(self.excluded_paths)
        ):
            limite = getattr(settings, 'SESSION_IDLE_TIMEOUT_MINUTES', 30) * 60
            ahora = time.time()
            ultima = request.session.get('ultima_actividad')
            if ultima and (ahora - ultima) > limite:
                auth_logout(request)
                return redirect('usuarios:login')
            if ultima is None or (ahora - ultima) >= self.MIN_INTERVALO:
                request.session['ultima_actividad'] = ahora
        return self.get_response(request)


class PasswordExpiryMiddleware:
    """Obliga a cambiar la contraseña vencida o en primer inicio de sesión."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = (
            '/usuarios/password/',
            '/usuarios/login/',
            '/usuarios/logout/',
            '/usuarios/verificar-2fa/',
            '/usuarios/configurar-2fa/',
            '/admin/',
            '/media/',
        )

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.path.startswith(self.excluded_paths)
            and request.user.password_vencida()
        ):
            if request.user.debe_cambiar_password:
                messages.error(request, 'Debes cambiar tu contraseña antes de continuar.')
            else:
                messages.warning(request, 'Tu contraseña caducó. Cambiarla antes de continuar.')
            return redirect('usuarios:cambiar_contrasena')
        return self.get_response(request)


class CentroMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.excluded_paths = (
            '/',  # home exact
            '/usuarios/login/',
            '/usuarios/logout/',
            '/usuarios/password/',
            '/dashboard-docente/',
            '/dashboard-admin/',
            '/estudiante/',
            '/seleccionar-centro/',
            '/admin/',
        )
        self.roles_sin_selector = ['docente', 'estudiante' ,'director', 'secretaria', 'cajero', 'tutor']

    def __call__(self, request):
        # ❌ Usar exact match
        if request.path in self.excluded_paths:
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        if user.is_superuser:
            return self.get_response(request)

        if user.rol in self.roles_sin_selector:
            return self.get_response(request)

        if not request.session.get('centro_id'):
            return redirect('core:seleccionar_centro')

        return self.get_response(request)


class PermisoPaginaMiddleware:
    """Verifica permisos de página según la configuración de PermisoPagina.

    Solo aplica a URLs que tengan un registro PermisoPagina activo.
    Los superusers y los URLs sin registro pasan sin restricción.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = (
            '/',
            '/usuarios/login/',
            '/usuarios/logout/',
            '/usuarios/password/',
            '/usuarios/verificar-2fa/',
            '/usuarios/configurar-2fa/',
            '/admin/',
            '/media/',
            '/static/',
            '/seleccionar-centro/',
        )

    def __call__(self, request):
        if (
            not request.user.is_authenticated
            or request.path.startswith(self.excluded_paths)
        ):
            return self.get_response(request)

        if request.user.is_superuser:
            return self.get_response(request)

        from django.urls import resolve
        from django.core.cache import cache

        try:
            match = resolve(request.path)
            url_name = match.url_name
            if match.app_name:
                url_name = f'{match.app_name}:{url_name}'
        except Exception:
            return self.get_response(request)

        cache_key = f'perm_mw:{url_name}'
        permiso = cache.get(cache_key)

        if permiso is None:
            from core.models import PermisoPagina
            permiso = PermisoPagina.objects.filter(
                url_name=url_name,
                activo=True,
            ).first()
            cache.set(cache_key, permiso, 300)

        if permiso is None:
            return self.get_response(request)

        user = request.user

        if permiso.roles_permitidos.filter(nombre=user.rol).exists():
            return self.get_response(request)

        if permiso.usuarios_permitidos.filter(pk=user.pk).exists():
            return self.get_response(request)

        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            '<h1>403 — Acceso denegado</h1>'
            '<p>No tienes permiso para acceder a esta página.</p>'
        )
