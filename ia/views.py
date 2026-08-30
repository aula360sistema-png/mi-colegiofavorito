from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .services import preguntar_ia


@login_required
@require_POST
@ratelimit(key='ip', rate='10/h', method=['POST'], block=True)
def prueba_ia(request):
    respuesta = preguntar_ia(
        "Dime un mensaje corto para estudiantes"
    )

    if respuesta.startswith("Error IA:"):
        return JsonResponse({
            "error": "La IA no está disponible en este momento. Inténtalo más tarde.",
        }, status=503)

    return JsonResponse({
        "respuesta": respuesta
    })

