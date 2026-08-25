"""Resolución de la configuración de correo y WhatsApp.

Los valores pueden venir de la base de datos (ConfiguracionCentro, por centro)
o, si quedaron vacíos, de settings/.env como respaldo.
"""

from django.conf import settings

from core.context_processors import obtener_configuracion_centro

# Host/puerto conocidos para los proveedores SMTP "de marca": el usuario
# no los edita, se autocompletan aquí para evitar errores de tipeo.
_HOSTS_SMTP_CONOCIDOS = {
    'smtp_gmail': {'host': 'smtp.gmail.com', 'port': 587, 'tls': True, 'ssl': False},
    'smtp_outlook': {'host': 'smtp.office365.com', 'port': 587, 'tls': True, 'ssl': False},
}


def obtener_configuracion_correo(centro):
    """Configuración de correo del centro, con fallback a settings.

    Devuelve un dict con al menos la clave 'proveedor'. Según el proveedor,
    incluye además: host/port/user/password/use_tls/use_ssl (SMTP) o
    api_key (Resend/SendGrid). Siempre incluye 'from_email'.

    Si no hay configuración en la BD ni en settings, el proveedor resuelve
    a 'consola' (Django imprime el correo en el log, no lo envía).
    """
    cfg = _configuracion_de(centro)

    if cfg:
        proveedor = cfg.email_proveedor or 'consola'
        from_email = cfg.email_remitente or settings.DEFAULT_FROM_EMAIL

        if proveedor in _HOSTS_SMTP_CONOCIDOS:
            preset = _HOSTS_SMTP_CONOCIDOS[proveedor]
            return {
                'proveedor': proveedor,
                'host': preset['host'],
                'port': preset['port'],
                'user': cfg.email_usuario,
                'password': cfg.email_clave,
                'use_tls': preset['tls'],
                'use_ssl': preset['ssl'],
                'from_email': from_email,
            }

        if proveedor in ('resend', 'sendgrid'):
            return {
                'proveedor': proveedor,
                'api_key': cfg.email_api_key,
                'from_email': from_email,
            }

        # 'smtp_otro' explícito, o configuraciones antiguas (creadas antes
        # de que existiera el selector) que solo llenaron email_servidor
        # sin fijar email_proveedor: en ambos casos hay un host manual.
        if proveedor == 'smtp_otro' or cfg.email_servidor:
            if cfg.email_servidor:
                return {
                    'proveedor': 'smtp_otro',
                    'host': cfg.email_servidor,
                    'port': cfg.email_puerto or 587,
                    'user': cfg.email_usuario,
                    'password': cfg.email_clave,
                    'use_tls': cfg.email_tls and not cfg.email_ssl,
                    'use_ssl': cfg.email_ssl,
                    'from_email': from_email,
                }

    # Fallback a settings/.env (comportamiento histórico, sin config en BD)
    if getattr(settings, 'EMAIL_HOST', ''):
        return {
            'proveedor': 'smtp_otro',
            'host': settings.EMAIL_HOST,
            'port': getattr(settings, 'EMAIL_PORT', 587),
            'user': getattr(settings, 'EMAIL_HOST_USER', ''),
            'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
            'use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
            'from_email': settings.DEFAULT_FROM_EMAIL,
        }

    return {'proveedor': 'consola', 'from_email': settings.DEFAULT_FROM_EMAIL}


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
