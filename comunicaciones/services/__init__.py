"""Lógica del módulo de comunicaciones: destinatarios, envío de campañas y
notificaciones de pago.
"""

import logging

from django.utils import timezone

logger = logging.getLogger('comunicaciones')


def construir_destinatarios(campania):
    """Genera los DestinatarioCampania según el alcance y canal de la campaña.

    Se re-ejecuta al crear la campaña o al modificarla; no duplica filas.
    """
    from comunicaciones.models import DestinatarioCampania

    tutores = _tutores_de_alcance(campania)
    canales = _canales_de(campania)

    creados = 0
    for tutor in tutores:
        for canal in canales:
            contacto = _contacto_de(tutor, canal)

            destinatario, fue_creado = DestinatarioCampania.objects.get_or_create(
                campania=campania,
                tutor=tutor,
                canal=canal,
                defaults={
                    'contacto': contacto,
                    'estado': 'pendiente',
                },
            )

            if not fue_creado:
                continue

            if not contacto:
                destinatario.estado = 'sin_contacto'
                destinatario.error = 'El tutor no tiene un contacto válido para este canal.'
                destinatario.save()
                continue

            creados += 1

    return creados


def procesar_campania(campania):
    """Envía todos los destinatarios pendientes de la campaña.

    Actualiza el estado de cada destinatario y el estado global de la campaña.
    """
    from comunicaciones.services.email import enviar_email
    from comunicaciones.services.whatsapp import enviar_whatsapp

    pendientes = campania.destinatarios.exclude(
        estado='enviado'
    ).select_related('tutor')

    envia_segun_canal = {
        'email': enviar_email,
        'whatsapp': enviar_whatsapp,
    }

    for destinatario in pendientes:
        _enviar_destinatario(destinatario, envia_segun_canal)

    _actualizar_estado_campania(campania)


def _enviar_destinatario(destinatario, envia_segun_canal):
    envia = envia_segun_canal.get(destinatario.canal)
    if envia is None:
        destinatario.estado = 'fallido'
        destinatario.error = 'Canal desconocido.'
        destinatario.save()
        return

    if not destinatario.contacto:
        destinatario.estado = 'sin_contacto'
        destinatario.error = 'El tutor no tiene un contacto válido para este canal.'
        destinatario.save()
        return

    try:
        envia(destinatario)
        destinatario.estado = 'enviado'
        destinatario.error = ''
        destinatario.enviado_at = timezone.now()
    except Exception as exc:  # noqa: BLE001 - no debe frenar el lote
        logger.exception('Fallo al enviar destinatario %s', destinatario.pk)
        destinatario.estado = 'fallido'
        destinatario.error = str(exc)[:1000]
        destinatario.enviado_at = timezone.now()

    destinatario.save()


def _actualizar_estado_campania(campania):
    total = campania.destinatarios.count()
    exitosos = campania.destinatarios.filter(estado='enviado').count()
    fallidos = campania.destinatarios.filter(estado='fallido').count()

    if total and exitosos == total:
        campania.estado = 'enviada'
    elif exitosos and fallidos == 0:
        campania.estado = 'enviada'
    elif exitosos:
        campania.estado = 'parcial'
    elif fallidos:
        campania.estado = 'fallida'
    else:
        campania.estado = 'borrador'

    campania.enviado_at = timezone.now()
    campania.save()


def notificar_pago(pago):
    """Notifica a los tutores del estudiante sobre un pago registrado.

    Se dispara automáticamente al registrar un pago. Envía correo y WhatsApp
    a cada tutor según los contactos disponibles y guarda un registro en
    NotificacionPago.
    """
    from comunicaciones.models import NotificacionPago
    from comunicaciones.services.email import enviar_email_pago
    from comunicaciones.services.whatsapp import enviar_whatsapp_pago

    tutores = pago.estudiante.tutores.filter(estado='activo')

    for tutor in tutores:
        if tutor.correo_personal:
            _notificar_pago_canal(
                pago, tutor, 'email', tutor.correo_personal, enviar_email_pago
            )

        if tutor.telefono:
            _notificar_pago_canal(
                pago, tutor, 'whatsapp', tutor.telefono, enviar_whatsapp_pago
            )


def _notificar_pago_canal(pago, tutor, canal, contacto, envia):
    from comunicaciones.models import NotificacionPago

    try:
        envia(pago, tutor, contacto)
        estado, error = 'enviado', ''
    except Exception as exc:  # noqa: BLE001 - la caja no debe fallar por esto
        logger.exception(
            'Fallo al notificar pago %s a %s por %s',
            pago.recibo or pago.id,
            tutor.nombre_completo(),
            canal,
        )
        estado, error = 'fallido', str(exc)[:1000]

    NotificacionPago.objects.create(
        centro=pago.centro,
        pago=pago,
        tutor=tutor,
        canal=canal,
        contacto=contacto,
        estado=estado,
        error=error,
    )


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _tutores_de_alcance(campania):
    if campania.alcance == 'seleccion':
        return campania.tutores.all()

    tutores = campania.centro.tutor_set.filter(estado='activo')

    if campania.alcance == 'grado' and campania.grado_id:
        from estudiantes.models import Inscripcion

        estudiantes_del_grado = (
            Inscripcion.objects
            .filter(
                centro=campania.centro,
                grado_id=campania.grado_id,
                anio_escolar__activo=True,
            )
            .values_list('estudiante_id', flat=True)
        )
        tutores = tutores.filter(estudiantes__in=estudiantes_del_grado)

    return tutores.distinct()


def _canales_de(campania):
    if campania.canal == 'ambos':
        return ['email', 'whatsapp']
    return [campania.canal]


def _contacto_de(tutor, canal):
    if canal == 'whatsapp':
        return (tutor.telefono or '').strip()
    return (tutor.correo_personal or '').strip()
