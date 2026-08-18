"""Resolución de la configuración de correo y WhatsApp.

Los valores pueden venir de la base de datos (ConfiguracionCentro, por centro)
o, si quedaron vacíos, de settings/.env como respaldo.
"""

from django.conf import settings

from core.context_processors import obtener_configuracion_centro


def obtener_configuracion_correo(centro):
    """Configuración SMTP del centro, con fallback a settings.

    Devuelve un dict con: host, port, user, password, use_tls, use_ssl,
    from_email. Si no hay datos en la BD ni en settings, host es '' (lo que
    dispara el backend de consola en desarrollo).
    """
    cfg = _configuracion_de(centro)

    if cfg and cfg.email_servidor:
        return {
            'host': cfg.email_servidor,
            'port': cfg.email_puerto or 587,
            'user': cfg.email_usuario,
            'password': cfg.email_clave,
            'use_tls': cfg.email_tls and not cfg.email_ssl,
            'use_ssl': cfg.email_ssl,
            'from_email': cfg.email_remitente or settings.DEFAULT_FROM_EMAIL,
        }

    return {
        'host': getattr(settings, 'EMAIL_HOST', ''),
        'port': getattr(settings, 'EMAIL_PORT', 587),
        'user': getattr(settings, 'EMAIL_HOST_USER', ''),
        'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
        'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
        'use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
        'from_email': settings.DEFAULT_FROM_EMAIL,
    }


def obtener_configuracion_whatsapp(centro):
    """Configuración del gateway WhatsApp del centro, con fallback a settings.

    Devuelve un dict con: url, token, remitente.
    """
    cfg = _configuracion_de(centro)

    if cfg and (cfg.whatsapp_url or cfg.whatsapp_token):
        return {
            'url': cfg.whatsapp_url,
            'token': cfg.whatsapp_token,
            'remitente': cfg.whatsapp_remitente,
        }

    return {
        'url': getattr(settings, 'WHATSAPP_GATEWAY_URL', ''),
        'token': getattr(settings, 'WHATSAPP_GATEWAY_TOKEN', ''),
        'remitente': getattr(settings, 'WHATSAPP_FROM', ''),
    }


def _configuracion_de(centro):
    if centro is None:
        return None
    return obtener_configuracion_centro(centro.id)
