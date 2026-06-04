# core/context_processors.py

from .models import ConfiguracionCentro

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

    return {
        'configuracion': configuracion
    }