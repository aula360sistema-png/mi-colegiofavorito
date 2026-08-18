"""Envío de mensajes de WhatsApp (módulo de comunicaciones).

El sistema habla con un gateway HTTP genérico que recibe un POST JSON con la
estructura que envía la mayoría de proveedores (Twilio, Meta Cloud API,
Wassenger, un gateway propio, etc.):

    POST {WHATSAPP_GATEWAY_URL}
    Authorization: Bearer {WHATSAPP_GATEWAY_TOKEN}
    {
      "to": "+1809XXXXXXX",
      "message": "...",
      "from": "{WHATSAPP_FROM}"   (opcional)
    }

Si WHATSAPP_GATEWAY_URL no está configurado, el envío se simula: se registra
en el log y se devuelve True para poder probar el flujo en desarrollo.
"""

import json
import logging
import re
import urllib.error
import urllib.request

from .configuracion import obtener_configuracion_whatsapp

logger = logging.getLogger('comunicaciones')


def enviar_whatsapp(destinatario):
    """Envía un WhatsApp a un DestinatarioCampania. Devuelve True si se envió."""
    campania = destinatario.campania
    mensaje = _personalizar(campania.mensaje, destinatario)
    return _enviar_http(
        destinatario.tutor.nombre_completo(),
        destinatario.contacto,
        mensaje,
        centro=campania.centro,
    )


def enviar_whatsapp_pago(pago, tutor, contacto):
    """Envía una notificación de pago a un tutor por WhatsApp."""
    mensaje = _mensaje_pago(pago, tutor)
    return _enviar_http(
        tutor.nombre_completo(),
        contacto,
        mensaje,
        centro=pago.centro,
    )


def _enviar_http(nombre_tutor, telefono, mensaje, centro=None):
    telefono = normalizar_telefono(telefono)

    if not telefono:
        logger.warning('WhatsApp: sin teléfono válido para %s', nombre_tutor)
        return False

    config = obtener_configuracion_whatsapp(centro)
    url = config['url']
    token = config['token']
    remitente = config['remitente']

    if not url:
        logger.info(
            '[SIMULADO] WhatsApp a %s (%s):\n%s',
            nombre_tutor,
            telefono,
            mensaje,
        )
        return True

    payload = {
        'to': telefono,
        'message': mensaje,
    }
    if remitente:
        payload['from'] = remitente

    cuerpo = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=cuerpo,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            estado = resp.getcode()
            logger.info(
                'WhatsApp enviado a %s (%s): HTTP %s',
                nombre_tutor,
                telefono,
                estado,
            )
            return 200 <= estado < 300
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode('utf-8', errors='replace')[:500]
        logger.error(
            'WhatsApp falló para %s (%s): HTTP %s %s',
            nombre_tutor,
            telefono,
            exc.code,
            detalle,
        )
        raise RuntimeError(
            f'El gateway de WhatsApp respondió HTTP {exc.code}: {detalle}'
        ) from exc
    except urllib.error.URLError as exc:
        logger.error(
            'WhatsApp falló para %s (%s): %s',
            nombre_tutor,
            telefono,
            exc.reason,
        )
        raise RuntimeError(f'No se pudo contactar el gateway: {exc.reason}') from exc


def normalizar_telefono(telefono):
    """Limpia un teléfono dominicano y le antepone +1 si no tiene país."""
    if not telefono:
        return ''

    solo_digitos = re.sub(r'\D', '', str(telefono))

    if len(solo_digitos) == 10:
        return f'+1{solo_digitos}'
    if len(solo_digitos) == 11 and solo_digitos.startswith('1'):
        return f'+{solo_digitos}'
    if solo_digitos.startswith('+') is False and len(solo_digitos) >= 12:
        return f'+{solo_digitos}'
    return solo_digitos


def _personalizar(texto, destinatario):
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


def _mensaje_pago(pago, tutor):
    return (
        f"Hola {tutor.nombre_completo()}, le informamos que se registró un "
        f"pago a nombre de {pago.estudiante.nombre_completo()}:\n"
        f"Concepto: {pago.concepto.nombre}\n"
        f"Monto: RD$ {pago.monto:,.2f}\n"
        f"Método: {pago.get_metodo_pago_display()}\n"
        f"Fecha: {pago.fecha:%d/%m/%Y}\n"
        f"Recibo No.: {pago.recibo or pago.id}"
    )
