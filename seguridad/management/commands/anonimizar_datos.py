import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from seguridad.models import RegistroRetencion
from seguridad.utils import (
    anonimizar_estudiante,
    anonimizar_historial_clinico,
    estudiantes_anonimizables,
)

logger = logging.getLogger('security')


class Command(BaseCommand):
    help = 'Anonimiza datos personales de estudiantes que superan el período de retención.'

    def handle(self, *args, **options):
        candidatos = estudiantes_anonimizables()
        count = 0
        for est in candidatos:
            campos = anonimizar_estudiante(est)
            hc = getattr(est, 'historial_clinico', None)
            if hc:
                anonimizar_historial_clinico(hc)
            count += 1
            logger.info(
                'ANONIMIZACIÓN: Estudiante %s - campos: %s',
                est.pk, campos,
            )

        RegistroRetencion.objects.create(
            tipo_dato='datos_personales',
            accion='anonimizacion',
            registros_afectados=count,
            detalle={
                'estudiantes_anonimizados': count,
                'ejecutado_automaticamente': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'Anonimización completada: {count} estudiante(s) procesado(s).'
        ))
