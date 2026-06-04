from administracion.models import Acta
from administracion.services.boletin import construir_boletin_estudiante


def generar_acta_estudiante(inscripcion, centro, anio, usuario):
    """
    Genera y guarda el ACTA (boletín oficial) de un estudiante.
    """

    datos = construir_boletin_estudiante(
        inscripcion=inscripcion,
        centro=centro,
        anio=anio
    )

    acta, creada = Acta.objects.update_or_create(
        centro=centro,
        anio_escolar=anio,
        estudiante=inscripcion.estudiante,
        defaults={
            "grado": inscripcion.grado,          # ✅ FK → instancia
            "seccion": str(inscripcion.seccion), # ✅ CharField → string
            "datos": datos,                      # ✅ JSON serializable
            "generado_por": usuario
        }
    )

    return acta, creada
