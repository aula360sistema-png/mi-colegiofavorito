from django.utils import timezone
from datetime import timedelta

from .models import Bitacora
from .services import registrar_evento


# ---------------------------------------------------
# MUCHOS LOGIN FALLIDOS
# ---------------------------------------------------

def detectar_login_fallidos(ip):

    hace_5_minutos = timezone.now() - timedelta(minutes=5)

    cantidad = Bitacora.objects.filter(
        accion='LOGIN_FAILED',
        ip=ip,
        fecha__gte=hace_5_minutos
    ).count()

    if cantidad >= 10:

        registrar_evento(
            accion='ALERTA',
            descripcion=f'Muchos intentos fallidos desde IP {ip}',
            modulo='SEGURIDAD',
            riesgo='CRITICO'
        )

        return True

    return False


# ---------------------------------------------------
# MUCHOS ELIMINADOS
# ---------------------------------------------------

def detectar_eliminaciones_masivas(usuario):

    hace_10_minutos = timezone.now() - timedelta(minutes=10)

    cantidad = Bitacora.objects.filter(
        usuario=usuario,
        accion='ELIMINAR',
        fecha__gte=hace_10_minutos
    ).count()

    if cantidad >= 15:

        registrar_evento(
            accion='ALERTA',
            descripcion=f'{usuario} eliminó demasiados registros',
            modulo='SEGURIDAD',
            riesgo='CRITICO'
        )

        return True

    return False


# ---------------------------------------------------
# MUCHAS EDICIONES MASIVAS
# ---------------------------------------------------

def detectar_ediciones_masivas(usuario):

    hace_5_minutos = timezone.now() - timedelta(minutes=5)

    cantidad = Bitacora.objects.filter(
        usuario=usuario,
        accion='EDITAR',
        fecha__gte=hace_5_minutos
    ).count()

    if cantidad >= 50:

        registrar_evento(
            accion='ALERTA',
            descripcion=f'{usuario} realizó demasiadas ediciones',
            modulo='ACADEMICO',
            riesgo='ALTO'
        )

        return True

    return False


# ---------------------------------------------------
# ACTIVIDAD SOSPECHOSA NOCTURNA
# ---------------------------------------------------

def detectar_actividad_nocturna(usuario):

    hora_actual = timezone.localtime().hour

    if hora_actual >= 1 and hora_actual <= 5:

        registrar_evento(
            accion='ALERTA',
            descripcion=f'Actividad nocturna detectada para {usuario}',
            modulo='SEGURIDAD',
            riesgo='MEDIO'
        )

        return True

    return False