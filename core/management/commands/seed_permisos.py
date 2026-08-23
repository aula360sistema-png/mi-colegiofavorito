from django.core.cache import cache
from django.core.management.base import BaseCommand

from core.models import PermisoPagina, RolCentro

ROLES_BASE = [
    'superadmin', 'admin', 'director', 'secretaria',
    'cajero', 'docente', 'tutor', 'estudiante',
]

# Matriz por defecto: refleja la visibilidad actual del sidebar.
# url_name -> (descripcion, [roles])
PERMISOS_DEFECTO = {
    # Docente
    'dashboard_docente': ('Panel del docente', ['docente']),
    # Estudiante
    'estudiante_inicio': ('Portal del estudiante', ['estudiante']),
    'estudiante_solicitudes': ('Certificados del estudiante', ['estudiante']),
    'estudiante_historial_clinico': ('Historial clínico (portal estudiante)', ['estudiante']),
    'comunicaciones:estudiante_comunicados': ('Comunicados (portal estudiante)', ['estudiante']),
    # Tutor
    'tutores:tutor_inicio': ('Panel del tutor', ['tutor']),
    'tutores:tutor_solicitudes': ('Certificados (portal tutor)', ['tutor']),
    'tutores:tutor_historial_clinico': ('Historial clínico (portal tutor)', ['tutor']),
    'comunicaciones:tutor_comunicados': ('Comunicados (portal tutor)', ['tutor']),
    # Administración común (director, secretaria, admin)
    'administracion:dashboard_admin': (
        'Panel administrativo', ['director', 'secretaria', 'admin', 'superadmin']),
    'administracion:reportes': (
        'Reportes académicos', ['director', 'secretaria', 'admin', 'superadmin']),
    'administracion:mantenimiento': (
        'Mantenimiento', ['director', 'secretaria', 'admin', 'superadmin']),
    'auditoria:bitacora': (
        'Bitácora del sistema', ['director', 'secretaria', 'admin', 'superadmin']),
    'seguridad:dashboard': (
        'Seguridad de datos', ['director', 'secretaria', 'admin', 'superadmin']),
    'estudiante_list': (
        'Listado de estudiantes', ['director', 'secretaria', 'admin', 'superadmin']),
    'estudiante_create': (
        'Nuevo estudiante', ['director', 'secretaria', 'admin', 'superadmin']),
    'historial_estudiantes': (
        'Historial de matrículas', ['director', 'secretaria', 'admin', 'superadmin']),
    'constancias': (
        'Constancias de estudiantes', ['director', 'secretaria', 'admin', 'superadmin']),
    'disciplina': (
        'Disciplina y conducta', ['director', 'secretaria', 'admin', 'superadmin']),
    'solicitudes_certificados': (
        'Solicitudes de certificados (panel)', ['director', 'secretaria', 'admin', 'superadmin']),
    'historial_clinico_list': (
        'Historial clínico (panel)', ['director', 'secretaria', 'admin', 'superadmin']),
    'tutores:tutor_list': (
        'Listado de tutores', ['director', 'secretaria', 'admin', 'superadmin']),
    'docente_list': (
        'Listado de docentes', ['director', 'secretaria', 'admin', 'superadmin']),
    'docente_create': ('Nuevo docente', ['secretaria', 'admin', 'superadmin']),
    # Solo dirección/administración
    'comunicaciones:campania_list': ('Campañas', ['director', 'admin', 'superadmin']),
    'comunicaciones:campania_create': ('Nueva campaña', ['director', 'admin', 'superadmin']),
    'comunicaciones:comunicado_list': ('Comunicados', ['director', 'admin', 'superadmin']),
    'comunicaciones:comunicado_create': ('Nuevo comunicado', ['director', 'admin', 'superadmin']),
    'nomina:dashboard': ('Nómina', ['director', 'admin', 'superadmin']),
    # Solo administración
    'core:home': ('Inicio general', ['admin', 'superadmin']),
    'usuarios:crear_miembro': ('Crear usuario', ['admin', 'superadmin']),
    'administracion:listado_personal': ('Personal', ['admin', 'superadmin']),
    'core:configuracion_centro': ('Configuración del centro', ['admin', 'superadmin']),
    'core:centro_list': ('Centros educativos', ['superadmin']),
}


def borrar_cache_permiso(url_name):
    cache.delete(f'perm_mw:{url_name}')
    cache.delete(f'perm_page:{url_name}')


class Command(BaseCommand):
    help = (
        'Crea/actualiza los permisos de página por defecto por rol '
        '(PermisoPagina) y los roles base en RolCentro. Idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-faltantes',
            action='store_true',
            help='No modifica permisos existentes; solo crea los que faltan.',
        )

    def handle(self, *args, **options):
        roles = {}
        for nombre in ROLES_BASE:
            roles[nombre], _ = RolCentro.objects.get_or_create(nombre=nombre)

        creados = 0
        actualizados = 0

        for url_name, (descripcion, nombres_roles) in PERMISOS_DEFECTO.items():
            permiso, created = PermisoPagina.objects.get_or_create(
                url_name=url_name,
                defaults={'descripcion': descripcion},
            )

            if options['solo_faltantes'] and not created:
                continue

            if not created:
                if permiso.descripcion != descripcion:
                    permiso.descripcion = descripcion
                    permiso.save(update_fields=['descripcion'])
                actualizados += 1
            else:
                creados += 1

            permiso.roles_permitidos.set(
                roles[nombre] for nombre in nombres_roles if nombre in roles
            )
            borrar_cache_permiso(url_name)

        resumen = f'{creados} creados'
        if not options['solo_faltantes']:
            resumen += f', {actualizados} actualizados'

        self.stdout.write(self.style.SUCCESS(
            f'Permisos por defecto sincronizados ({resumen}). '
            f'Sin registro = página abierta a todos los autenticados.'
        ))
