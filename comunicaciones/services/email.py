"""Envío de correos electrónicos (módulo de comunicaciones).

La configuración SMTP puede venir de la base de datos (por centro) o de
settings/.env como respaldo. Si no hay SMTP configurado, Django usa el
backend de consola (imprime en terminal) para desarrollo.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection, send_mail

from .configuracion import obtener_configuracion_correo

logger = logging.getLogger('comunicaciones')


def enviar_email(destinatario):
    """Envía un correo a un DestinatarioCampania.

    Devuelve True si se envió; lanza excepción ante error (el llamador decide
    cómo registrar el fallo).
    """
    campania = destinatario.campania
    asunto = _personalizar(campania.asunto, destinatario)
    mensaje = _personalizar(campania.mensaje, destinatario)

    logger.info(
        'Enviando email de campaña %s a %s (%s)',
        campania.id,
        destinatario.tutor.nombre_completo(),
        destinatario.contacto,
    )

    config = obtener_configuracion_correo(campania.centro)

    send_mail(
        asunto,
        mensaje,
        config['from_email'],
        [destinatario.contacto],
        connection=_conexion(config),
        fail_silently=False,
    )
    return True


def enviar_email_pago(pago, tutor, contacto):
    """Envía una notificación de pago a un tutor por correo."""
    asunto = f"Notificación de pago · {pago.estudiante.nombre_completo()}"
    mensaje = _mensaje_pago(pago, tutor)

    logger.info(
        'Enviando email de pago %s a %s (%s)',
        pago.recibo or pago.id,
        tutor.nombre_completo(),
        contacto,
    )

    config = obtener_configuracion_correo(pago.centro)

    send_mail(
        asunto,
        mensaje,
        config['from_email'],
        [contacto],
        connection=_conexion(config),
        fail_silently=False,
    )
    return True


def enviar_email_con_pdf(asunto, mensaje, destinatario, archivo_nombre, pdf_bytes, centro):
    """Envía un correo con un PDF adjunto usando la config SMTP del centro."""
    config = obtener_configuracion_correo(centro)

    logger.info(
        'Enviando email con adjunto a %s (%s)',
        destinatario,
        archivo_nombre,
    )

    email = EmailMessage(
        asunto,
        mensaje,
        config['from_email'],
        [destinatario],
        connection=_conexion(config),
    )
    email.attach(archivo_nombre, pdf_bytes, 'application/pdf')
    email.send(fail_silently=False)
    return True


def enviar_correo_prueba(centro, destino):
    """Envía un correo de prueba a `destino` usando la config del centro.

    Útil para validar desde la pantalla de configuración que los datos SMTP
    son correctos. Lanza excepción si falla la conexión/envío.
    """
    config = obtener_configuracion_correo(centro)
    conexion = _conexion(config)

    logger.info('Enviando correo de prueba del centro %s a %s', centro.id, destino)

    send_mail(
        'Correo de prueba · Comunicaciones',
        (
            'Este es un correo de prueba enviado desde la configuración de '
            'Comunicaciones de su centro.\n\n'
            'Si lo recibe, la configuración de correo es correcta.'
        ),
        config['from_email'],
        [destino],
        connection=conexion,
        fail_silently=False,
    )
    return True


def _conexion(config):
    if not config['host']:
        return get_connection()

    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config['host'],
        port=config['port'],
        username=config['user'],
        password=config['password'],
        use_tls=config['use_tls'],
        use_ssl=config['use_ssl'],
        timeout=getattr(settings, 'EMAIL_TIMEOUT', 30),
        fail_silently=False,
    )


def _mensaje_pago(pago, tutor):
    return (
        f"Hola {tutor.nombre_completo()},\n\n"
        f"Hemos registrado un pago a nombre de {pago.estudiante.nombre_completo()}.\n\n"
        f"  Concepto: {pago.concepto.nombre}\n"
        f"  Monto: RD$ {pago.monto:,.2f}\n"
        f"  Método: {pago.get_metodo_pago_display()}\n"
        f"  Fecha: {pago.fecha:%d/%m/%Y}\n"
        f"  Recibo No.: {pago.recibo or pago.id}\n\n"
        f"Gracias por su confianza."
    )


def _personalizar(texto, destinatario):
    """Reemplaza los tokens {{tutor}} y {{estudiante}} con datos reales."""
    tutor = destinatario.tutor
    estudiantes = tutor.estudiantes.all()
    primer_estudiante = estudiantes.first()
    nombre_estudiante = (
        primer_estudiante.nombre_completo()
        if primer_estudiante
        else 'su(s) hijo(s)'
    )

    return (
        texto
        .replace('{{tutor}}', tutor.nombre_completo())
        .replace('{{estudiante}}', nombre_estudiante)
    )
