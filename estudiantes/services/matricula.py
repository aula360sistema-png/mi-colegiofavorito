import re
import unicodedata
from datetime import date

from ..models import Estudiante


def _letra_inicial(texto):
    if not texto:
        return ''
    limpio = unicodedata.normalize(
        'NFKD', texto
    ).encode('ascii', 'ignore').decode('ascii')
    palabra = re.findall(r'[A-Za-z]', limpio)
    return palabra[0].upper() if palabra else ''


def iniciales_estudiante(primer_nombre, segundo_nombre,
                         primer_apellido, segundo_apellido):
    iniciales = (
        _letra_inicial(primer_nombre),
        _letra_inicial(segundo_nombre),
        _letra_inicial(primer_apellido),
        _letra_inicial(segundo_apellido),
    )
    return ''.join(iniciales)


def iniciales_centro(centro):
    iniciales = ''.join(
        _letra_inicial(palabra)
        for palabra in re.split(r'\s+', centro.nombre or '')
        if palabra
    )
    return iniciales[:3]


def siguiente_secuencia(centro, anio):
    max_secuencia = 0
    for matricula in Estudiante.objects.filter(
        centro=centro,
        matricula__contains=f"-{anio}-",
    ).values_list('matricula', flat=True):
        partes = [p for p in matricula.split('-') if p]
        if (
            len(partes) >= 3
            and partes[1] == str(anio)
            and partes[2].isdigit()
        ):
            max_secuencia = max(max_secuencia, int(partes[2]))
    return max_secuencia + 1


def generar_matricula(estudiante, anio=None):
    anio = anio or date.today().year
    iniciales = iniciales_estudiante(
        estudiante.primer_nombre,
        estudiante.segundo_nombre,
        estudiante.primer_apellido,
        estudiante.segundo_apellido,
    )
    secuencia = siguiente_secuencia(estudiante.centro, anio)
    return "{}-{}-{:06d}-{}".format(
        iniciales,
        anio,
        secuencia,
        iniciales_centro(estudiante.centro),
    )