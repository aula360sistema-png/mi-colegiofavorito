import logging

from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def role_required(*roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('usuarios:login')

            if request.user.rol not in roles:
                logger.warning(
                    'Acceso denegado para %s (rol %s) a %s',
                    request.user,
                    request.user.rol,
                    request.path
                )

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'No tienes permisos para acceder aquí.'
                    }, status=403)

                return render(
                    request,
                    '403.html',
                    status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


from core.utils.session import get_centro_activo


def centro_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        centro = get_centro_activo(request)

        if not centro:
            return redirect('core:seleccionar_centro')

        request.centro = centro

        return view_func(request, *args, **kwargs)

    return wrapper


def ajax_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if request.headers.get('x-requested-with') != 'XMLHttpRequest':

            return JsonResponse({
                'error': 'Petición inválida'
            }, status=400)

        return view_func(request, *args, **kwargs)

    return wrapper