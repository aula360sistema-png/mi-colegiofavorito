"""
Inicialización idempotente para el primer deploy (Render free, sin Shell).

    python manage.py seed_inicial

1. Crea el superadmin desde DJANGO_SUPERUSER_* (si no existe).
2. Si la base NO tiene centros educativos, siembra datos demo:
   seed_demo (centro principal) + seed_permisos.

Seguro de ejecutar en cada deploy: nunca borra ni duplica datos
existentes; si ya hay un centro, omite las semillas.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import CentroEducativo


class Command(BaseCommand):
    help = 'Superadmin + semillas solo si la base está vacía (idempotente).'

    def handle(self, *args, **options):
        try:
            call_command('bootstrap_superuser', verbosity=0)
            self.stdout.write('bootstrap_superuser: OK')
        except SystemExit:
            self.stdout.write(
                'AVISO: sin DJANGO_SUPERUSER_PASSWORD no se creó el '
                'superadmin. Defínela en Environment y vuelve a desplegar.'
            )

        if CentroEducativo.objects.exists():
            self.stdout.write(
                'La base ya tiene centros: omito seed_demo/seed_permisos.'
            )
            return

        self.stdout.write('Base vacía: sembrando datos demo...')
        call_command('seed_permisos')
        call_command('seed_demo')
        self.stdout.write(self.style.SUCCESS('Semillas iniciales creadas.'))
