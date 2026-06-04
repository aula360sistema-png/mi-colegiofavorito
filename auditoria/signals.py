from django.apps import apps

from django.db.models.signals import (
    pre_save,
    post_save,
    post_delete
)

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed
)

from .utils import (
    registrar_automatico,
    convertir_modelo_dict
)

from .models import Bitacora


# Guardaremos snapshots temporales
_estados_anteriores = {}


# Modelos que NO queremos auditar
EXCLUIR_MODELOS = [
    'Bitacora',
    'Session',
    'LogEntry',
]


def guardar_estado_anterior(sender, instance, **kwargs):

    if sender.__name__ in EXCLUIR_MODELOS:
        return

    if instance.pk:

        try:
            anterior = sender.objects.get(pk=instance.pk)

            _estados_anteriores[
                (sender.__name__, instance.pk)
            ] = convertir_modelo_dict(anterior)

        except sender.DoesNotExist:
            pass


def registrar_guardado(sender, instance, created, **kwargs):

    if sender.__name__ in EXCLUIR_MODELOS:
        return

    accion = 'CREAR' if created else 'EDITAR'

    datos_anteriores = None

    if not created:

        datos_anteriores = _estados_anteriores.get(
            (sender.__name__, instance.pk)
        )

    datos_nuevos = convertir_modelo_dict(instance)

    registrar_automatico(
        instancia=instance,
        accion=accion,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )


def registrar_eliminado(sender, instance, **kwargs):

    if sender.__name__ in EXCLUIR_MODELOS:
        return

    registrar_automatico(
        instancia=instance,
        accion='ELIMINAR',
        datos_anteriores=convertir_modelo_dict(instance),
        datos_nuevos=None
    )


# LOGIN
def registrar_login(sender, request, user, **kwargs):

    registrar_automatico(
        instancia=user,
        accion='LOGIN'
    )


# LOGOUT
def registrar_logout(sender, request, user, **kwargs):

    if user:

        registrar_automatico(
            instancia=user,
            accion='LOGOUT'
        )


# LOGIN FAILED
def registrar_login_fallido(sender, credentials, request, **kwargs):

    class FakeUser:
        pk = None

        def __str__(self):
            return credentials.get('username', 'DESCONOCIDO')

        class __class__:
            __name__ = 'AUTH'

    registrar_automatico(
        instancia=FakeUser(),
        accion='LOGIN_FAILED'
    )


def conectar_signals():

    # Conectar todos los modelos
    for model in apps.get_models():

        if model.__name__ in EXCLUIR_MODELOS:
            continue

        pre_save.connect(
            guardar_estado_anterior,
            sender=model
        )

        post_save.connect(
            registrar_guardado,
            sender=model
        )

        post_delete.connect(
            registrar_eliminado,
            sender=model
        )

    # Auth signals
    user_logged_in.connect(registrar_login)

    user_logged_out.connect(registrar_logout)

    user_login_failed.connect(registrar_login_fallido)