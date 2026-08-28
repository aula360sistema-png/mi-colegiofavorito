from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from academico.models import (
    Periodo,
    DocenteMateria,
    Competencia,
    Calificacion
)

def redondear(valor):
    return float(
        Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _normalizar_periodo(nombre):
    """Convierte 'p1' -> 'P1' para mostrar de forma consistente."""
    texto = (nombre or "").strip()
    if texto[:1].lower() == "p" and texto[1:].isdigit():
        return f"P{texto[1:]}"
    return texto


def enriquecer_boletin_para_vista(datos):
    """
    Prepara el snapshot del Acta para MOSTRAR (no modifica la BD).
    Agrega:
      - etiquetas de período normalizadas (P1, P2...)
      - 'promedios': promedio de cada período sobre las competencias del área
      - 'nota_completivo' y 'completivo_aprueba' por área
      - 'semestres': agrupación de los períodos en semestres
    """
    datos = dict(datos or {})

    periodos = datos.get("periodos", [])
    n_periodos = len(periodos)

    semestre = {}
    mitad = n_periodos // 2
    if n_periodos:
        if mitad >= 1:
            semestre["1"] = list(range(0, mitad))
        if n_periodos - mitad >= 1:
            semestre["2"] = list(range(mitad, n_periodos))
    datos["semestres"] = [
        {"nombre": f"Semestre {clave}", "indices": indices}
        for clave, indices in semestre.items()
    ]

    completivo = datos.get("completivo") or {}
    completivo_map = {}
    for det in (completivo.get("detalle") or []):
        completivo_map[det.get("asignatura")] = {
            "nota": det.get("nota_completivo"),
            "aprueba": det.get("aprueba"),
        }

    asignaturas_raw = datos.get("asignaturas", [])

    asignaturas = []
    for asignatura in asignaturas_raw:
        asignatura = dict(asignatura)
        competencias = asignatura.get("competencias", [])

        promedios = []
        for idx in range(n_periodos):
            valores = []
            for c in competencias:
                per = c.get("periodos", [])
                if idx < len(per):
                    nota = per[idx].get("nota")
                    if nota is not None:
                        valores.append(float(nota))
            promedios.append(
                redondear(sum(valores) / len(valores)) if valores else None
            )

        asignatura["promedios"] = promedios

        detalle = completivo_map.get(asignatura.get("asignatura"))
        asignatura["nota_completivo"] = detalle.get("nota") if detalle else None
        asignatura["completivo_aprueba"] = detalle.get("aprueba") if detalle else None

        asignaturas.append(asignatura)

    datos["asignaturas"] = asignaturas
    datos["periodos"] = [_normalizar_periodo(p) for p in periodos]
    return datos


def construir_boletin_estudiante(inscripcion, centro, anio):

    # 🔒 Los períodos de completivo y extraordinario NO entran en el promedio
    # base (MINERD: las calificaciones parciales del año son solo los períodos
    # regulares; completivo y extraordinario se evalúan por separado).
    periodos = list(
        Periodo.objects.filter(
            estados__anio_escolar=anio,
            estados__cerrado=True,
            es_completivo=False,
            es_extraordinario=False
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

        # Las competencias son del catálogo MINERD del nivel: todas las
        # asignaturas de ese nivel muestran las mismas competencias en el boletín.
        competencias_catalogo = Competencia.objects.filter(
            nivel=inscripcion.grado.nivel,
            activo=True
        ).order_by("nombre")

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

        for competencia in competencias_catalogo:
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

            # PC = promedio de la competencia: promedio de sus calificaciones
            # por período  -> (P1+P2+P3+P4)/4  (Art. 49 / Art. 30-e MINERD)
            pc = redondear(sum(valores) / len(valores)) if valores else None
            if pc is not None:
                pcs.append(pc)

            competencias_data.append({
                "competencia": competencia.nombre,
                "periodos": periodos_data,
                "pc": pc
            })

        # PF = promedio final del área: promedio de los PCs de sus competencias
        # -> (C1+C2+C3)/3  (Art. 30-f MINERD)
        pf = redondear(sum(pcs) / len(pcs)) if pcs else None

        asignaturas_map[asignatura.id] = {
            "asignatura_id": asignatura.id,
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


def resultado_completivo_estudiante(inscripcion, centro, anio, nota_minima):
    """
    Evalúa el período de completivo (es_completivo=True) para una inscripción.

    Regla MINERD (Ordenanza 04-2023, Art. 51 y Art. 80):
    La evaluación completiva vale 50% y la calificación final obtenida durante
    el año (el promedio de calificaciones parciales, que es el pf del área)
    representa el otro 50%. Aprueba la asignatura cuya calificación final
    combinada sea igual o superior a la nota mínima:

        final = (nota_completivo * 0.50) + (pf * 0.50)

    Solo se toman en cuenta los períodos de completivo cerrados. Si no existe
    ninguno, devuelve None. El estudiante aprueba el completivo cuando TODAS
    las asignaturas reprobadas en el promedio base aprueban con el combinado.
    """

    completivo_periodos = list(
        Periodo.objects.filter(
            estados__anio_escolar=anio,
            estados__cerrado=True,
            es_completivo=True
        ).order_by("orden")
    )

    if not completivo_periodos:
        return None

    base = construir_boletin_estudiante(inscripcion, centro, anio)

    reprobadas = [
        a for a in base["asignaturas"]
        if a.get("pf") is not None and a["pf"] < nota_minima
    ]

    if not reprobadas:
        return {"aprobado": True, "detalle": []}

    # Notas del completivo por asignatura (promedio de calificaciones)
    completivo_notas = {}

    asignaciones = DocenteMateria.objects.filter(
        grado=inscripcion.grado,
        seccion=inscripcion.seccion,
        anio_escolar=anio
    ).select_related("asignatura")

    for asignacion in asignaciones:
        asignatura = asignacion.asignatura

        if asignatura.id in completivo_notas:
            continue

        calificaciones = Calificacion.objects.filter(
            inscripcion=inscripcion,
            asignatura=asignatura,
            periodo__in=completivo_periodos,
            nota__isnull=False
        )

        if calificaciones.exists():
            promedio = (
                sum(float(c.nota) for c in calificaciones)
                / calificaciones.count()
            )
            completivo_notas[asignatura.id] = redondear(promedio)

    detalle = []
    aprobado = True

    for a in reprobadas:
        nota_completivo = completivo_notas.get(a["asignatura_id"])
        # MINERD Art. 51/80: completiva 50% + promedio parcial del año (pf) 50%
        if nota_completivo is not None and a.get("pf") is not None:
            final = redondear(
                (nota_completivo * 0.50) + (a["pf"] * 0.50)
            )
            aprueba = final >= nota_minima
        else:
            final = None
            aprueba = False

        if not aprueba:
            aprobado = False

        detalle.append({
            "asignatura": a["asignatura"],
            "pf": a["pf"],
            "nota_completivo": nota_completivo,
            "final": final,
            "aprueba": aprueba
        })

    return {"aprobado": aprobado, "detalle": detalle}


def resultado_extraordinario_estudiante(inscripcion, centro, anio, nota_minima):
    """
    Evalúa el período extraordinario (es_extraordinario=True) para una inscripción.

    Reglas MINERD (Ordenanza 04-2023):
    - Evaluación extraordinaria vale 70%; la calificación final del año de la
      asignatura (pf) representa el 30% restante (Art. 52 y Art. 81):

        final = (nota_extraordinario * 0.70) + (pf * 0.30)

      La calificación mínima aprobatoria es la nota mínima.
    - Repetición: Primaria (3ro-6to) reprueba con 4+ asignaturas; 1-3 =
      promoción condicional. Secundaria: reprueba con 3+ asignaturas; 1-2 =
      promoción condicional.

    Devuelve dict con:
      aprobado: True/False/None (None = sin cambios)
      condicional: True si promueve condicionalmente
      repite: True si debe repetir
      detalle: lista de asignaturas evaluadas
    """

    extraordinario_periodos = list(
        Periodo.objects.filter(
            estados__anio_escolar=anio,
            estados__cerrado=True,
            es_extraordinario=True
        ).order_by("orden")
    )

    if not extraordinario_periodos:
        return None

    base = construir_boletin_estudiante(inscripcion, centro, anio)

    reprobadas = [
        a for a in base["asignaturas"]
        if a.get("pf") is not None and a["pf"] < nota_minima
    ]

    if not reprobadas:
        return {"aprobado": True, "condicional": False, "repite": False, "detalle": []}

    extraordinario_notas = {}

    asignaciones = DocenteMateria.objects.filter(
        grado=inscripcion.grado,
        seccion=inscripcion.seccion,
        anio_escolar=anio
    ).select_related("asignatura")

    for asignacion in asignaciones:
        asignatura = asignacion.asignatura

        if asignatura.id in extraordinario_notas:
            continue

        calificaciones = Calificacion.objects.filter(
            inscripcion=inscripcion,
            asignatura=asignatura,
            periodo__in=extraordinario_periodos,
            nota__isnull=False
        )

        if calificaciones.exists():
            promedio = (
                sum(float(c.nota) for c in calificaciones)
                / calificaciones.count()
            )
            extraordinario_notas[asignatura.id] = redondear(promedio)

    detalle = []
    aprueba_todas = True

    for a in reprobadas:
        nota_extraordinario = extraordinario_notas.get(a["asignatura_id"])
        # MINERD Art. 52/81: extraordinaria 70% + calificación final del año (pf) 30%
        if nota_extraordinario is not None and a.get("pf") is not None:
            final = redondear(
                (nota_extraordinario * 0.70) + (a["pf"] * 0.30)
            )
            aprueba = final >= nota_minima
        else:
            final = None
            aprueba = False

        if not aprueba:
            aprueba_todas = False

        detalle.append({
            "asignatura": a["asignatura"],
            "pf": a["pf"],
            "nota_extraordinario": nota_extraordinario,
            "final": final,
            "aprueba": aprueba
        })

    total_reprobadas = len(reprobadas)
    no_aprobadas = sum(1 for d in detalle if not d["aprueba"])

    # Determinar si es primaria o secundaria
    # Primaria: 3ro-6to; Secundaria: 1ro-6to
    es_primaria = (
        inscripcion.grado.nivel
        and inscripcion.grado.nivel.nombre.lower().startswith("primar")
    )

    if aprueba_todas:
        return {"aprobado": True, "condicional": False, "repite": False, "detalle": detalle}

    # No aprobó todas: aplicar regla de repetición
    if es_primaria:
        # Primaria: 4+ reprobadas = repite; 1-3 = condicional
        repite = no_aprobadas >= 4
    else:
        # Secundaria: 3+ reprobadas = repite; 1-2 = condicional
        repite = no_aprobadas >= 3

    return {
        "aprobado": False,
        "condicional": not repite,
        "repite": repite,
        "detalle": detalle
    }
