from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .services import preguntar_ia

def prueba_ia(request):

    respuesta = preguntar_ia(
        "Dime un mensaje corto para estudiantes"
    )

    return JsonResponse({
        "respuesta": respuesta
    })

