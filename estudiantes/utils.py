from academico.models import Grado
from .models import Inscripcion

def validar_promocion_estudiante(estudiante, anio_actual):

    ultima = (
        Inscripcion.objects
        .filter(estudiante=estudiante)
        .exclude(anio_escolar=anio_actual)
        .select_related('grado', 'anio_escolar')
        .order_by('-anio_escolar__fecha_fin')
        .first()
    )

    if not ultima:
        return {
            "permitido": True,
            "grado_permitido": None,
            "mensaje": "Estudiante nuevo"
        }

    # 🔥 VALIDACIÓN REAL DEL AÑO
    if not ultima.anio_escolar.cerrado:
        return {
            "permitido": False,
            "grado_permitido": None,
            "mensaje": f"El año escolar {ultima.anio_escolar} aún no ha sido cerrado."
        }

    if ultima.estado_final in ('reprobado', 'recuperacion'):
        return {
            "permitido": True,
            "grado_permitido": ultima.grado,
            "mensaje": f"Debe repetir {ultima.grado}."
        }

    if ultima.estado_final == 'sin_calificacion':
        return {
            "permitido": True,
            "grado_permitido": ultima.grado,
            "mensaje": f"Debe repetir {ultima.grado} (no posee calificación final)."
        }

    # ✅ APROBADO: pasa al grado siguiente según el orden del nivel
    siguiente = (
        Grado.objects
        .filter(
            nivel=ultima.grado.nivel,
            orden__gt=ultima.grado.orden
        )
        .order_by('orden', 'nombre')
        .first()
    )

    if siguiente:
        return {
            "permitido": True,
            "grado_permitido": siguiente,
            "mensaje": f"Puede pasar a {siguiente}."
        }

    return {
        "permitido": True,
        "grado_permitido": None,
        "mensaje": "Último grado del nivel. Sin restricción de grado."
    }