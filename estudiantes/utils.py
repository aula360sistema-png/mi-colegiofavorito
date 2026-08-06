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

    if ultima.estado_final == 'reprobado':
        return {
            "permitido": True,
            "grado_permitido": ultima.grado,
            "mensaje": f'Debe repetir {ultima.grado}.'
        }

    if ultima.estado_final == 'promovido':
        return {
            "permitido": True,
            "grado_permitido_id": ultima.grado_id + 1,
            "mensaje": "Puede pasar al grado siguiente."
        }

    return {
        "permitido": True,
        "grado_permitido": None,
        "mensaje": ""
    }