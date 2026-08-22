"""Crea un backup de la base de datos, sea SQLite o PostgreSQL.

Detecta automáticamente el motor configurado en el .env (DB_ENGINE) y usa el
método adecuado:

- SQLite:  API de backup en caliente de Python (no bloquea la app, segura
           incluso mientras hay escrituras). Antes hace un checkpoint WAL.
- PostgreSQL: pg_dump en formato custom (-Fc), comprimido y apto para
           restore selectivo con pg_restore.

Los archivos se guardan en backups/ con marca de tiempo. Esa carpeta está
ignorada por git; copia los backups a un destino externo (nube u otro disco).

Uso:
    python manage.py backup_db                  # un backup
    python manage.py backup_db --keep 14        # conserva solo los 14 más recientes
    python manage.py backup_db --dest D:\\backups
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Backup de la base de datos (SQLite o PostgreSQL según .env).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep', type=int, default=0,
            help='Conserva solo los N backups más recientes (retención).')
        parser.add_argument(
            '--dest', type=str, default='',
            help='Directorio destino (por defecto: backups/ del proyecto).')

    def handle(self, *args, **options):
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']
        dest = Path(options['dest']) if options['dest'] else Path('backups')
        dest.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        if engine.endswith('sqlite3'):
            archivo = self._backup_sqlite(db_settings, dest, timestamp)
        elif engine.endswith('postgresql'):
            archivo = self._backup_postgres(db_settings, dest, timestamp)
        else:
            raise CommandError(f'Motor no soportado: {engine}')

        self.stdout.write(self.style.SUCCESS(f'Backup creado: {archivo}'))

        if options['keep']:
            eliminados = self._aplicar_retencion(dest, options['keep'])
            for nombre in eliminados:
                self.stdout.write(f'Retenido fuera: {nombre}')

    # ------------------------------------------------------------------ #
    def _backup_sqlite(self, db_settings, dest, timestamp):
        """Backup en caliente usando la API backup() del módulo sqlite3."""
        import sqlite3

        origen = Path(str(db_settings['NAME']))
        if not origen.exists():
            raise CommandError(f'No existe la BD: {origen}')

        destino = dest / f'mcf_sqlite_{timestamp}.sqlite3'

        conn = sqlite3.connect(origen)
        try:
            # Checkpoint del WAL: vuelca el journal pendiente al archivo principal.
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE);')
            backup_conn = sqlite3.connect(destino)
            try:
                with backup_conn:
                    conn.backup(backup_conn)
            finally:
                backup_conn.close()
        finally:
            conn.close()

        return destino

    def _backup_postgres(self, db_settings, dest, timestamp):
        """Backup con pg_dump en formato custom (restore vía pg_restore)."""
        pg_dump = shutil.which('pg_dump')
        if not pg_dump:
            raise CommandError(
                'pg_dump no está en el PATH. Instala PostgreSQL Client Tools '
                '(o instala PostgreSQL completo) y vuelve a intentarlo.')

        destino = dest / f'mcf_postgres_{timestamp}.dump'
        host = db_settings.get('HOST') or '127.0.0.1'
        port = db_settings.get('PORT') or '5432'
        user = db_settings.get('USER') or ''

        cmd = [
            pg_dump,
            '--format=custom',
            '--compress=6',
            '--file', str(destino),
            '--host', host,
            '--port', str(port),
            '--username', user,
            '--no-password',
            db_settings['NAME'],
        ]

        # PGPASSWORD evita el prompt interactivo; no se imprime nunca.
        env = os.environ.copy()
        if db_settings.get('PASSWORD'):
            env['PGPASSWORD'] = db_settings['PASSWORD']

        resultado = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if resultado.returncode != 0:
            raise CommandError(f'pg_dump falló: {resultado.stderr.strip() or "sin detalle"}')
        return destino

    # ------------------------------------------------------------------ #
    @staticmethod
    def _aplicar_retencion(dest, keep):
        patrones = ('mcf_sqlite_*.sqlite3', 'mcf_postgres_*.dump')
        backups = []
        for patron in patrones:
            backups.extend(dest.glob(patron))
        backups.sort(key=lambda p: p.name, reverse=True)

        eliminados = []
        for viejo in backups[keep:]:
            viejo.unlink()
            eliminados.append(viejo.name)
        return eliminados
