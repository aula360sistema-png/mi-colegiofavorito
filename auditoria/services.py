from .models import Bitacora
from .middleware import get_current_request
from .utils import (
    obtener_ip,
    obtener_navegador,
    detectar_dispositivo
)


def registrar_evento(

    accion,
    descripcion,

    usuario=None,

    modulo='SISTEMA',

    modelo=None,

    objeto_id=None,

    riesgo='BAJO',

    datos_anteriores=None,

    datos_nuevos=None
):

    request = get_current_request()

    ip = None
    ruta = None
    metodo = None
    navegador = None
    dispositivo = None

    # Obtener usuario automáticamente
    if request:

        if not usuario and request.user.is_authenticated:
            usuario = request.user

        ip = obtener_ip(request)

        ruta = request.path

        metodo = request.method

        navegador = obtener_navegador(request)

        dispositivo = detectar_dispositivo(navegador)

    Bitacora.objects.create(

        usuario=usuario,

        accion=accion,

        modulo=modulo,

        descripcion=descripcion,

        modelo=modelo,

        objeto_id=objeto_id,

        ip=ip,

        ruta=ruta,

        metodo=metodo,

        navegador=navegador,

        tipo_dispositivo=dispositivo,

        riesgo=riesgo,

        datos_anteriores=datos_anteriores,

        datos_nuevos=datos_nuevos
    )