import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('comunicaciones')


class Command(BaseCommand):
    help = 'Envía notificaciones automáticas a tutores por pagos vencidos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--centro', type=int, default=None,
            help='ID del centro a procesar. Si se omite, procesa todos.',
        )

    def handle(self, *args, **options):
        from core.models import CentroEducativo, AnioEscolar
        from caja.services import deuda_detalle_estudiante
        from comunicaciones.models import NotificacionPagoVencida
        from comunicaciones.services.email import enviar_email_vencimiento
        from comunicaciones.services.whatsapp import (
            enviar_whatsapp_vencimiento,
            normalizar_telefono,
        )
        from estudiantes.models import Estudiante
        from tutores.models import Tutor

        centro_id = options.get('centro')
        centros = CentroEducativo.objects.filter(activo=True)
        if centro_id:
            centros = centros.filter(id=centro_id)

        total_notificados = 0
        total_errores = 0

        for centro in centros:
            anio = AnioEscolar.objects.filter(centro=centro, activo=True).first()
            if not anio:
                continue

            estudiantes = Estudiante.objects.filter(
                centro=centro,
                inscripciones__anio_escolar=anio,
                inscripciones__estado_final='pendiente',
            ).distinct()

            for estudiante in estudiantes:
                deuda = deuda_detalle_estudiante(centro, estudiante, anio)
                if not deuda['tiene_deuda'] or deuda['vencida'] <= 0:
                    continue

                hoy = timezone.localdate()
                ya_notificado = NotificacionPagoVencida.objects.filter(
                    centro=centro,
                    estudiante=estudiante,
                    fecha=hoy,
                ).exists()
                if ya_notificado:
                    continue

                tutores = Tutor.objects.filter(
                    estudiantes=estudiante,
                    centro=centro,
                    estado='activo',
                )

                for tutor in tutores:
                    total_notificados, total_errores = self._notificar_email(
                        tutor, estudiante, deuda, centro, hoy,
                        total_notificados, total_errores,
                    )
                    total_notificados, total_errores = self._notificar_whatsapp(
                        tutor, estudiante, deuda, centro, hoy,
                        total_notificados, total_errores,
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Notificaciones de vencimiento enviadas: {total_notificados}, '
            f'errores: {total_errores}'
        ))

    def _notificar_email(self, tutor, estudiante, deuda, centro, hoy,
                         total_notificados, total_errores):
        from comunicaciones.models import NotificacionPagoVencida
        from comunicaciones.services.email import enviar_email_vencimiento

        if not tutor.correo_personal:
            return total_notificados, total_errores

        try:
            enviar_email_vencimiento(centro, tutor, estudiante, deuda)
            NotificacionPagoVencida.objects.create(
                centro=centro,
                estudiante=estudiante,
                tutor=tutor,
                canal='email',
                contacto=tutor.correo_personal,
                estado='enviado',
                fecha=hoy,
                monto_vencido=deuda['vencida'],
            )
            total_notificados += 1
        except Exception as e:
            logger.warning(
                'Error enviando email vencimiento a %s: %s', tutor, e,
            )
            NotificacionPagoVencida.objects.create(
                centro=centro,
                estudiante=estudiante,
                tutor=tutor,
                canal='email',
                contacto=tutor.correo_personal,
                estado='fallido',
                error=str(e),
                fecha=hoy,
                monto_vencido=deuda['vencida'],
            )
            total_errores += 1

        return total_notificados, total_errores

    def _notificar_whatsapp(self, tutor, estudiante, deuda, centro, hoy,
                            total_notificados, total_errores):
        from comunicaciones.models import NotificacionPagoVencida
        from comunicaciones.services.whatsapp import (
            enviar_whatsapp_vencimiento,
            normalizar_telefono,
        )

        telefono = normalizar_telefono(tutor.telefono)
        if not telefono:
            return total_notificados, total_errores

        try:
            enviar_whatsapp_vencimiento(tutor, estudiante, deuda)
            NotificacionPagoVencida.objects.create(
                centro=centro,
                estudiante=estudiante,
                tutor=tutor,
                canal='whatsapp',
                contacto=telefono,
                estado='enviado',
                fecha=hoy,
                monto_vencido=deuda['vencida'],
            )
            total_notificados += 1
        except Exception as e:
            logger.warning(
                'Error enviando WhatsApp vencimiento a %s: %s', tutor, e,
            )
            NotificacionPagoVencida.objects.create(
                centro=centro,
                estudiante=estudiante,
                tutor=tutor,
                canal='whatsapp',
                contacto=telefono,
                estado='fallido',
                error=str(e),
                fecha=hoy,
                monto_vencido=deuda['vencida'],
            )
            total_errores += 1

        return total_notificados, total_errores
