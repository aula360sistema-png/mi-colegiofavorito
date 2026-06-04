from .models import Bitacora
from .middleware import get_current_request


def obtener_ip(request):

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def obtener_navegador(request):

    return request.META.get('HTTP_USER_AGENT', '')


def detectar_dispositivo(user_agent):

    agent = user_agent.lower()

    if 'mobile' in agent:
        return 'MOVIL'

    elif 'tablet' in agent:
        return 'TABLET'

    return 'PC'


def calcular_riesgo(accion):

    riesgos = {
        'LOGIN': 'BAJO',
        'LOGOUT': 'BAJO',
        'LOGIN_FAILED': 'MEDIO',
        'CREAR': 'MEDIO',
        'EDITAR': 'MEDIO',
        'ELIMINAR': 'ALTO',
    }

    return riesgos.get(accion, 'BAJO')


def convertir_modelo_dict(instancia):

    datos = {}

    for field in instancia._meta.fields:

        try:
            valor = getattr(instancia, field.name)

            if hasattr(valor, 'id'):
                valor = valor.id

            datos[field.name] = str(valor)

        except Exception:
            pass

    return datos


def registrar_automatico(
    instancia,
    accion,
    datos_anteriores=None,
    datos_nuevos=None
):

    request = get_current_request()

    usuario = None
    ip = None
    ruta = None
    metodo = None
    navegador = None
    dispositivo = None

    if request:

        if request.user.is_authenticated:
            usuario = request.user

        ip = obtener_ip(request)

        ruta = request.path

        metodo = request.method

        navegador = obtener_navegador(request)

        dispositivo = detectar_dispositivo(navegador)

    Bitacora.objects.create(

        usuario=usuario,

        accion=accion,

        modulo=instancia.__class__.__name__.upper(),

        descripcion=f"{accion} en {str(instancia)}",

        modelo=instancia.__class__.__name__,

        objeto_id=instancia.pk,

        ip=ip,

        ruta=ruta,

        metodo=metodo,

        navegador=navegador,

        tipo_dispositivo=dispositivo,

        riesgo=calcular_riesgo(accion),

        datos_anteriores=datos_anteriores,

        datos_nuevos=datos_nuevos
    )