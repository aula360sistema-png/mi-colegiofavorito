import hashlib
import logging
import re
from datetime import date

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

logger = logging.getLogger(__name__)


def _get_fernet():
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured(
            'ENCRYPTION_KEY no está definida. Los campos cifrados no pueden '
            'guardarse en texto plano (fail-closed).'
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def cifrar_campo(valor):
    if not valor or not str(valor).strip():
        return valor
    f = _get_fernet()
    return f.encrypt(str(valor).encode()).decode()


def descifrar_campo(valor):
    if not valor:
        return valor
    f = _get_fernet()
    try:
        return f.decrypt(valor.encode()).decode()
    except Exception:
        logger.error('No se pudo descifrar un valor almacenado (clave rotada o dato corrupto).')
        return valor


def anonimizar_nombre(nombre):
    if not nombre:
        return '***'
    if len(nombre) == 1:
        return '*'
    return nombre[0] + '*' * (len(nombre) - 1)


def anonimizar_cedula(cedula):
    if not cedula or len(cedula) < 4:
        return '****'
    return cedula[:2] + '*' * (len(cedula) - 2)


def anonimizar_telefono(telefono):
    if not telefono or len(telefono) < 4:
        return '****'
    return '*' * (len(telefono) - 4) + telefono[-4:]


def anonimizar_email(email):
    if not email or '@' not in email:
        return '***@***.***'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"{'*' * len(local)}@{domain}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"


def anonimizar_estudiante(estudiante):
    campos = {}
    if estudiante.primer_nombre:
        estudiante.primer_nombre = anonimizar_nombre(estudiante.primer_nombre)
        campos['primer_nombre'] = estudiante.primer_nombre
    if estudiante.segundo_nombre:
        estudiante.segundo_nombre = anonimizar_nombre(estudiante.segundo_nombre)
        campos['segundo_nombre'] = estudiante.segundo_nombre
    if estudiante.primer_apellido:
        estudiante.primer_apellido = anonimizar_nombre(estudiante.primer_apellido)
        campos['primer_apellido'] = estudiante.primer_apellido
    if estudiante.segundo_apellido:
        estudiante.segundo_apellido = anonimizar_nombre(estudiante.segundo_apellido)
        campos['segundo_apellido'] = estudiante.segundo_apellido
    if estudiante.matricula:
        estudiante.matricula = f"ANON-{hashlib.md5(estudiante.matricula.encode()).hexdigest()[:8].upper()}"
        campos['matricula'] = estudiante.matricula
    if estudiante.lugar_nacimiento:
        estudiante.lugar_nacimiento = '***'
        campos['lugar_nacimiento'] = '***'
    if estudiante.direccion:
        estudiante.direccion = '***'
        campos['direccion'] = '***'
    if estudiante.nombre_tutor:
        estudiante.nombre_tutor = anonimizar_nombre(estudiante.nombre_tutor)
        campos['nombre_tutor'] = estudiante.nombre_tutor
    if estudiante.cedula_tutor:
        estudiante.cedula_tutor = anonimizar_cedula(estudiante.cedula_tutor)
        campos['cedula_tutor'] = estudiante.cedula_tutor
    if estudiante.telefono_tutor:
        estudiante.telefono_tutor = anonimizar_telefono(estudiante.telefono_tutor)
        campos['telefono_tutor'] = estudiante.telefono_tutor
    estudiante.save()
    return campos


def anonimizar_historial_clinico(historial):
    campos_anonimizados = {}
    campos_sensibles = [
        'alergias', 'condiciones_medicas', 'medicamentos_habituales',
        'vacunas', 'observaciones',
        'contacto_emergencia_nombre', 'contacto_emergencia_telefono',
        'contacto_emergencia_secundario_nombre',
        'contacto_emergencia_secundario_telefono',
    ]
    for campo in campos_sensibles:
        valor = getattr(historial, campo, '')
        if valor:
            setattr(historial, campo, '***DATOS CLÍNICOS ANONIMIZADOS***')
            campos_anonimizados[campo] = True
    historial.save()
    return campos_anonimizados


def estudiantes_para_retencion(anio_limite=None):
    from estudiantes.models import Estudiante
    if anio_limite is None:
        anio_limite = date.today().year - settings.DATA_RETENTION_YEARS
    estudiantes_ids = set()
    for inscripcion in __import__('estudiantes.models', fromlist=['Inscripcion']).Inscripcion.objects.filter(
        anio_escolar__anio__lte=anio_limite,
    ).values_list('estudiante_id', flat=True):
        estudiantes_ids.add(inscripcion)
    return Estudiante.objects.filter(id__in=estudiantes_ids)


def estudiantes_anonimizables(anio_limite=None):
    from estudiantes.models import Estudiante
    if anio_limite is None:
        anio_limite = date.today().year - settings.DATA_RETENTION_ANONYMIZE_AFTER_YEARS
    estudiantes_ids = set()
    for inscripcion in __import__('estudiantes.models', fromlist=['Inscripcion']).Inscripcion.objects.filter(
        anio_escolar__anio__lte=anio_limite,
    ).values_list('estudiante_id', flat=True):
        estudiantes_ids.add(inscripcion)
    return Estudiante.objects.filter(
        id__in=estudiantes_ids,
        primer_nombre__isnull=False,
    ).exclude(primer_nombre__startswith='*')
