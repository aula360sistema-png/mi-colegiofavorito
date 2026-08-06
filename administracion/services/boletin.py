from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from academico.models import (
    Periodo,
    DocenteMateria,
    AreaCompetencia,
    Calificacion
)

def redondear(valor):
    return float(
        Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def construir_boletin_estudiante(inscripcion, centro, anio):

    periodos = list(
        Periodo.objects.filter(
            centro=centro,
            anio_escolar=anio,
            cerrado=True
        ).order_by("orden")
    )

    if not periodos:
        raise ValueError("No hay períodos cerrados para generar boletines")

    asignaciones = DocenteMateria.objects.filter(
        grado=inscripcion.grado,
        seccion=inscripcion.seccion,
        anio_escolar=anio
    ).select_related("asignatura")

    asignaturas_map = {}  # 🔒 CLAVE ANTI-DUPLICADO

    for asignacion in asignaciones:
        asignatura = asignacion.asignatura

        if asignatura.id in asignaturas_map:
            continue  # ⛔ ya procesada

        area_competencias = AreaCompetencia.objects.filter(
            area=asignatura.area
        ).select_related("competencia")

        calificaciones = Calificacion.objects.filter(
            inscripcion=inscripcion,
            asignatura=asignatura,
            periodo__in=periodos
        )

        notas = defaultdict(dict)
        for c in calificaciones:
            if c.nota is not None:
                notas[c.competencia_id][c.periodo_id] = float(c.nota)

        competencias_data = []
        pcs = []

        for ac in area_competencias:
            competencia = ac.competencia
            valores = []
            periodos_data = []

            for p in periodos:
                nota = notas.get(competencia.id, {}).get(p.id)

                if nota is not None:
                    valores.append(nota)

                periodos_data.append({
                    "periodo": p.nombre,
                    "nota": nota
                })

            pc = redondear(sum(valores) / len(valores)) if valores else None
            if pc is not None:
                pcs.append(pc)

            competencias_data.append({
                "competencia": competencia.nombre,
                "periodos": periodos_data,
                "pc": pc
            })

        pf = redondear(sum(pcs) / len(pcs)) if pcs else None

        asignaturas_map[asignatura.id] = {
            "asignatura": asignatura.nombre,
            "competencias": competencias_data,
            "pf": pf
        }
        

    return {
        "centro": centro.nombre,
        "anio_escolar": str(anio),
        "estudiante": {
            "nombre": inscripcion.estudiante.nombre_completo(),
            "matricula": inscripcion.id,
            "grado": str(inscripcion.grado),
            "seccion": str(inscripcion.seccion),
        },
        "periodos": [p.nombre for p in periodos],
        "asignaturas": list(asignaturas_map.values())  # 👈 sin duplicados
    }
