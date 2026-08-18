"""Estructura académica oficial del sistema educativo dominicano (MINERD).

Niveles, ciclos y grados según la Ordenanza 03-2013 y el diseño curricular
del Ministerio de Educación de la República Dominicana:

- Nivel Inicial (0 a 6 años):
    * Primer ciclo: Maternal, Infantes, Párvulos (45 días a 2 años 11 meses)
    * Segundo ciclo: Pre-Kínder, Kínder, Preprimario (3 a 5 años 11 meses)
- Nivel Primario (6 a 11 años):
    * Primer ciclo: 1ro a 3ro de Primaria
    * Segundo ciclo: 4to a 6to de Primaria
- Nivel Secundario (12 a 17 años):
    * Primer ciclo: 1ro a 3ro de Secundaria (antes 7mo, 8vo y 1ro de media)
    * Segundo ciclo: 4to a 6to de Secundaria (antes 2do, 3ro y 4to de bachiller)
"""

# Competencias con las que se califica en el centro.
# Especificadas por el centro (4): las siete Competencias Fundamentales del
# currículo MINERD quedaron agrupadas en cuatro.
COMPETENCIAS_FUNDAMENTALES_MINERD = [
    "Competencia Comunicativa",
    "Competencia Pensamiento Lógico, Creativo y Crítico y Resolución de Problemas",
    "Competencia Científica y Tecnológica y Ambiental y de la Salud",
    "Competencia Ética y Ciudadana y Desarrollo Personal y Espiritual",
]

ESTRUCTURA_MINERD = {
    "inicial": {
        "nombre": "Nivel Inicial",
        "edades": "0 a 6 años",
        "ciclos": [
            {
                "ciclo": 1,
                "grados": ["Maternal", "Infantes", "Párvulos"],
            },
            {
                "ciclo": 2,
                "grados": ["Pre-Kínder", "Kínder", "Preprimario"],
            },
        ],
    },
    "primaria": {
        "nombre": "Nivel Primario",
        "edades": "6 a 11 años",
        "ciclos": [
            {
                "ciclo": 1,
                "grados": [
                    "1ro de Primaria",
                    "2do de Primaria",
                    "3ro de Primaria",
                ],
            },
            {
                "ciclo": 2,
                "grados": [
                    "4to de Primaria",
                    "5to de Primaria",
                    "6to de Primaria",
                ],
            },
        ],
    },
    "secundaria": {
        "nombre": "Nivel Secundario",
        "edades": "12 a 17 años",
        "ciclos": [
            {
                "ciclo": 1,
                "grados": [
                    "1ro de Secundaria",
                    "2do de Secundaria",
                    "3ro de Secundaria",
                ],
            },
            {
                "ciclo": 2,
                "grados": [
                    "4to de Secundaria",
                    "5to de Secundaria",
                    "6to de Secundaria",
                ],
            },
        ],
    },
}


def grados_minerd(tipo):
    """Lista de (orden, ciclo, nombre_grado) para un tipo de nivel."""
    datos = ESTRUCTURA_MINERD.get(tipo)
    if not datos:
        return []
    grados = []
    orden = 1
    for ciclo in datos["ciclos"]:
        for nombre in ciclo["grados"]:
            grados.append((orden, ciclo["ciclo"], nombre))
            orden += 1
    return grados


def tipos_disponibles():
    """Devuelve las claves de nivel disponibles (inicial, primaria, secundaria)."""
    return list(ESTRUCTURA_MINERD.keys())


def crear_estructura_minerd(centro, tipos):
    """Crea (de forma idempotente) los niveles y grados MINERD de un centro.

    No borra nada: si un nivel o grado ya existe lo deja intacto y solo
    completa lo que falte.
    """
    from academico.models import Grado, Nivel

    niveles = []
    grados = []

    for tipo in tipos:
        datos = ESTRUCTURA_MINERD.get(tipo)
        if not datos:
            continue

        nivel, creado = Nivel.objects.get_or_create(
            centro=centro,
            tipo=tipo,
            defaults={"nombre": datos["nombre"]},
        )
        if not creado and nivel.nombre != datos["nombre"]:
            nivel.nombre = datos["nombre"]
            nivel.save(update_fields=["nombre"])
        niveles.append(nivel)

        for orden, ciclo, nombre in grados_minerd(tipo):
            grado, creado = Grado.objects.get_or_create(
                nivel=nivel,
                nombre=nombre,
                defaults={"orden": orden, "ciclo": ciclo},
            )
            if not creado:
                cambios = {}
                if grado.orden != orden:
                    cambios["orden"] = orden
                if grado.ciclo != ciclo:
                    cambios["ciclo"] = ciclo
                if cambios:
                    Grado.objects.filter(pk=grado.pk).update(**cambios)
            grados.append(grado)

    return {"niveles": niveles, "grados": grados}


def cambiar_estructura_minerd(centro, tipo):
    """Establece ``tipo`` como el ÚNICO nivel del centro.

    Reglas:
    - Si el centro ya tiene niveles de otros tipos SIN registros
      (inscripciones, historiales, actas, asignaciones de docente, etc.)
      los elimina y genera los grados de ``tipo``.
    - Si hay registros dependientes en otro nivel, NO cambia nada y
      devuelve ``{'status': 'bloqueado', 'niveles': [...]}``.
    """
    from academico.models import GradoAsignatura, Nivel, DocenteMateria
    from administracion.models import Acta
    from docentes.models import AsignacionDocente
    from estudiantes.models import HistorialAcademico, Inscripcion

    otros = Nivel.objects.filter(centro=centro).exclude(tipo=tipo)
    if otros.exists():
        for nivel in otros:
            con_datos = (
                Inscripcion.objects.filter(grado__nivel=nivel).exists()
                or HistorialAcademico.objects.filter(grado__nivel=nivel).exists()
                or Acta.objects.filter(grado__nivel=nivel).exists()
                or DocenteMateria.objects.filter(grado__nivel=nivel).exists()
                or GradoAsignatura.objects.filter(grado__nivel=nivel).exists()
                or AsignacionDocente.objects.filter(grado__nivel=nivel).exists()
            )
            if con_datos:
                return {
                    "status": "bloqueado",
                    "niveles": list(otros),
                }
        otros.delete()

    resultado = crear_estructura_minerd(centro, [tipo])
    resultado["status"] = "ok"
    return resultado
