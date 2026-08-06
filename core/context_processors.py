# core/context_processors.py

from .models import ConfiguracionCentro
from core.utils.centro import obtener_centro_del_usuario

def configuracion_centro(request):

    centro_id = request.session.get('centro_id')

    configuracion = None

    if centro_id:

        try:

            configuracion = ConfiguracionCentro.objects.get(
                centro_id=centro_id
            )

        except ConfiguracionCentro.DoesNotExist:
            pass

    if configuracion is None and request.user.is_authenticated:

        centro = obtener_centro_del_usuario(request)

        if centro:

            configuracion = getattr(
                centro,
                'configuracioncentro',
                None,
            )

    return {
        'configuracion': configuracion
    }