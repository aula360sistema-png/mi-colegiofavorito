"""
Crea el superadmin inicial desde variables de entorno (idempotente).

Pensado para el primer deploy (Render → Shell):

    python manage.py bootstrap_superuser

Variables esperadas:
    DJANGO_SUPERUSER_USERNAME (default: admin)
    DJANGO_SUPERUSER_EMAIL
    DJANGO_SUPERUSER_PASSWORD (requerida)

Si el usuario ya existe no hace nada (no toca su contraseña).
"""

import os

from django.core.management.base import BaseCommand

from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Crea el superadmin inicial desde DJANGO_SUPERUSER_* si no existe.'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')

        if not password:
            self.stderr.write(
                'ERROR: define DJANGO_SUPERUSER_PASSWORD en el entorno.'
            )
            raise SystemExit(1)

        if Usuario.objects.filter(username=username).exists():
            self.stdout.write(
                f'El superadmin "{username}" ya existe: nada que hacer.'
            )
            return

        Usuario.objects.create_superuser(
            username=username,
            email=email or f'{username}@example.com',
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Superadmin "{username}" creado. '
                'Recuerda configurar el 2FA en el primer login.'
            )
        )
