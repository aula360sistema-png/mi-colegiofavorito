from django.utils import timezone
from django.utils.crypto import get_random_string


def generar_referencia_pago(solicitud):
    return f"ONL-{timezone.now().strftime('%Y%m%d%H%M%S')}-{get_random_string(6).upper()}"


def procesar_pago_online(solicitud):
    """Procesa el pago en línea de una solicitud de certificado.

    PUNTO DE INTEGRACIÓN CON LA PASARELA DE PAGO.
    Aquí se conectará el proveedor real (CardNet, VISA, MasterCard,
    ACH, etc.) cuando el módulo de pagos se implemente.

    Por ahora genera una referencia simulada y marca la solicitud
    como pagada para no bloquear el flujo.

    Retorna (referencia, mensaje_error).
    """
    try:
        from core.models import ConfiguracionCentro
        config = ConfiguracionCentro.objects.filter(
            centro=solicitud.estudiante.centro
        ).first()

        if config and not config.permitir_pago_online:
            return None, "El pago en línea no está habilitado para este centro."

        referencia = generar_referencia_pago(solicitud)
        solicitud.pagado = True
        solicitud.metodo_pago = 'online'
        solicitud.referencia_pago = referencia
        solicitud.pagado_en = timezone.now()
        solicitud.estado = 'pagada'
        solicitud.save()
        return referencia, None

    except Exception as e:
        return None, f"Error procesando el pago: {e}"


def reembolsar_pago_online(solicitud):
    """Revierte un pago en línea (anulación de la solicitud).

    PUNTO DE INTEGRACIÓN CON LA PASARELA DE PAGO.
    """
    solicitud.pagado = False
    solicitud.referencia_pago = ""
    solicitud.pagado_en = None
    solicitud.save()
