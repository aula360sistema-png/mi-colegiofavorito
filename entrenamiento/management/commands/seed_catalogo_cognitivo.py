"""Siembra el catálogo del entrenamiento cognitivo.

Catálogo global (no por centro), inspirado en el esquema de Progrentis pero
con destrezas definidas por categorías cognitivas propias:

- 6 tramos de edad (5-6, 7-9, 10-12, 13-15, 16-18, 18+).
- 6 destrezas por tramo (una por categoría).
- 8 unidades por tramo (cada una ejercita 3 destrezas).
- 1 ejercicio por destreza en cada unidad (banco inicial funcional).

Idempotente: usa update_or_create; se puede ejecutar las veces que se quiera.

Uso:
    python manage.py seed_catalogo_cognitivo
"""

from django.core.management.base import BaseCommand

from entrenamiento.models import (
    DestrezaCognitiva,
    Ejercicio,
    TramoEdad,
    UnidadEntrenamiento,
)

TRAMOS = [
    ("aprestamiento", "Aprestamiento (5-6 años)", 5, 6, 1),
    ("destrezas_i", "Destrezas I (7-9 años)", 7, 9, 2),
    ("destrezas_ii", "Destrezas II (10-12 años)", 10, 12, 3),
    ("destrezas_iii", "Destrezas III (13-15 años)", 13, 15, 4),
    ("paisajes", "Paisajes competenciales (16-18 años)", 16, 18, 5),
    ("espacio", "Espacio de entrenamiento (18+ años)", 18, 99, 6),
]

DESTREZAS = {
    "aprestamiento": [
        ("atencion", "Atención sostenida y focalizada",
         "Mantener el foco en la tarea e ignorar distracciones."),
        ("memoria", "Memoria de trabajo (reglas y consignas)",
         "Retener consignas e información brevemente para resolver la tarea."),
        ("lectura", "Conciencia fonológica y letras",
         "Reconocimiento de letras y sonidos iniciales."),
        ("comprension", "Comprensión de consignas orales",
         "Entender y ejecutar instrucciones sencillas."),
        ("logica", "Clasificación, series y cantidad",
         "Agrupar, ordenar y contar elementos cotidianos."),
        ("metacognicion", "Inhibición de respuestas impulsivas",
         "Esperar y verificar antes de responder."),
    ],
    "destrezas_i": [
        ("atencion", "Rastreo visual y atención selectiva",
         "Localizar un estímulo entre distractores."),
        ("memoria", "Memoria de trabajo y actualización",
         "Actualizar información en memoria a medida que cambia la tarea."),
        ("lectura", "Fluidez y precisión lectora",
         "Leer con velocidad y sin errores."),
        ("comprension", "Comprensión literal de textos breves",
         "Extraer información explícita de un texto corto."),
        ("logica", "Cálculo mental y series numéricas",
         "Resolver operaciones sencillas y continuar patrones."),
        ("metacognicion", "Planificación de tareas sencillas",
         "Anticipar pasos antes de realizar una tarea."),
    ],
    "destrezas_ii": [
        ("atencion", "Atención dividida y mantenimiento del foco",
         "Atender a dos fuentes de información sin perder la tarea."),
        ("memoria", "Memoria de trabajo y codificación",
         "Codificar y manipular información verbal y visual."),
        ("lectura", "Fluidez lectora y vocabulario",
         "Leer con ritmo y ampliar el léxico."),
        ("comprension", "Comprensión inferencial",
         "Deducir información implícita del texto."),
        ("logica", "Razonamiento lógico y resolución de problemas",
         "Aplicar reglas y estrategias a problemas estructurados."),
        ("metacognicion", "Autorregulación y verificación",
         "Revisar la propia respuesta antes de darla por válida."),
    ],
    "destrezas_iii": [
        ("atencion", "Control atencional ante distractores",
         "Mantener el rendimiento a pesar de la interferencia."),
        ("memoria", "Memoria de trabajo y organización",
         "Organizar y manipular varios elementos en memoria."),
        ("lectura", "Lectura eficiente de información",
         "Localizar información relevante en textos densos."),
        ("comprension", "Comprensión crítica y múltiples fuentes",
         "Comparar y contrastar información de distintas fuentes."),
        ("logica", "Pensamiento computacional y problemas no estructurados",
         "Descomponer problemas y diseñar soluciones en pasos."),
        ("metacognicion", "Monitoreo metacognitivo y toma de decisiones",
         "Evaluar el propio progreso y decidir cuándo cambiar de estrategia."),
    ],
    "paisajes": [
        ("atencion", "Foco sostenido en tareas complejas",
         "Sostener la atención durante tareas largas y exigentes."),
        ("memoria", "Transferencia de información",
         "Aplicar información aprendida en contextos nuevos."),
        ("lectura", "Lectura académica y densidad informativa",
         "Procesar textos con alta densidad de información."),
        ("comprension", "Argumentación y análisis de discursos",
         "Identificar tesis, evidencia y sesgos."),
        ("logica", "Modelización y resolución creativa",
         "Representar problemas y generar soluciones originales."),
        ("metacognicion", "Autorregulación del aprendizaje",
         "Planificar, monitorear y evaluar el propio estudio."),
    ],
    "espacio": [
        ("atencion", "Atención y adaptabilidad",
         "Ajustar el foco atencional ante cambios de contexto."),
        ("memoria", "Memoria operativa y flexibilidad",
         "Alternar entre reglas y mantener información activa."),
        ("lectura", "Lectura profesional eficaz",
         "Extraer lo esencial de documentos extensos."),
        ("comprension", "Síntesis y pensamiento crítico",
         "Integrar información y evaluar conclusiones."),
        ("logica", "Razonamiento analítico aplicado",
         "Usar datos y modelos para tomar decisiones."),
        ("metacognicion", "Aprendizaje autodirigido",
         "Identificar necesidades de aprendizaje y buscar recursos."),
    ],
}

UNIDADES_NOMBRES = [
    "Atención y rastreo visual",
    "Memoria en acción",
    "Fluidez lectora",
    "Comprensión de textos",
    "Lógica y cálculo",
    "Series y patrones",
    "Pensamiento crítico",
    "Autorregulación",
]

# Categorías que ejercita cada unidad (una destreza por categoría).
CATEGORIAS_POR_UNIDAD = {
    1: ['atencion', 'memoria', 'lectura'],
    2: ['memoria', 'comprension', 'atencion'],
    3: ['lectura', 'comprension', 'logica'],
    4: ['comprension', 'logica', 'metacognicion'],
    5: ['logica', 'memoria', 'lectura'],
    6: ['logica', 'atencion', 'comprension'],
    7: ['metacognicion', 'comprension', 'lectura'],
    8: ['metacognicion', 'atencion', 'logica'],
}

# Base de dificultad por tramo (1-5).
DIFICULTAD_BASE = {
    "aprestamiento": 1,
    "destrezas_i": 1,
    "destrezas_ii": 2,
    "destrezas_iii": 3,
    "paisajes": 3,
    "espacio": 4,
}

PERFIL_TRAMO = {
    "aprestamiento": {
        "animales": ["oso", "pez", "sol", "luna", "nube"],
        "objetos": ["casa", "lápiz", "pelota", "flor", "silla"],
        "secuencia": ["lunes", "martes", "miércoles"],
        "num_min": 1,
        "num_max": 5,
        "hechos": [
            ("1 + 1 = 3", False),
            ("El sol sale durante el día", True),
            ("Los peces vuelan", False),
        ],
        "pasaje": "El gato duerme en la cama. El gato es de color negro.",
    },
    "destrezas_i": {
        "animales": ["perro", "gato", "pájaro", "pez", "conejo"],
        "objetos": ["libro", "mochila", "crayón", "regla", "cuaderno"],
        "secuencia": ["lunes", "martes", "miércoles", "jueves", "viernes"],
        "num_min": 1,
        "num_max": 30,
        "hechos": [
            ("5 × 2 = 10", True),
            ("El año tiene 20 meses", False),
            ("La rana es un reptil", False),
        ],
        "pasaje": "El niño llevó su perro al parque. El perro corría detrás de la pelota.",
    },
    "destrezas_ii": {
        "animales": ["tortuga", "camaleón", "delfín", "búho", "leopardo"],
        "objetos": ["diccionario", "calculadora", "brújula", "termómetro", "mapamundi"],
        "secuencia": ["enero", "marzo", "mayo", "julio", "septiembre"],
        "num_min": 10,
        "num_max": 99,
        "hechos": [
            ("Los ángulos de un triángulo suman 180°", True),
            ("El agua hierve a 0°C", False),
            ("La Tierra gira alrededor del Sol", True),
        ],
        "pasaje": "En la biblioteca se prestan libros por una semana. Quien no devuelve el libro a tiempo paga una multa simbólica.",
    },
    "destrezas_iii": {
        "animales": ["murciélago", "armadillo", "colibrí", "tucán", "manatí"],
        "objetos": ["reloj", "semáforo", "brújula", "telescopio", "microscopio"],
        "secuencia": ["lunes", "miércoles", "viernes", "domingo"],
        "num_min": 100,
        "num_max": 999,
        "hechos": [
            ("La célula es la unidad básica de los seres vivos", True),
            ("El ADN solo existe en los animales", False),
            ("La fotosíntesis la realizan las plantas", True),
        ],
        "pasaje": "Los humedales regulan el agua de lluvia y albergan cientos de especies. Su desaparición afecta a la biodiversidad y a las comunidades cercanas.",
    },
    "paisajes": {
        "animales": ["gorila", "rinoceronte", "cóndor", "jaguar", "guacamayo"],
        "objetos": ["presupuesto", "currículo", "estadística", "legislación", "infraestructura"],
        "secuencia": ["hipótesis", "axioma", "heurística", "inferencia"],
        "num_min": 1000,
        "num_max": 9999,
        "hechos": [
            ("La Constitución es la norma suprema del Estado", True),
            ("La memoria RAM almacena información de forma permanente", False),
            ("Un ensayo argumentativo defiende una tesis", True),
        ],
        "pasaje": "La lectura crítica exige identificar la tesis, valorar la evidencia y reconocer sesgos. Es una competencia que se entrena y se transfiere a cualquier disciplina.",
    },
    "espacio": {
        "animales": ["bisontes", "nutrias", "cetáceos", "aves rapaces", "anfibios"],
        "objetos": ["analítica", "heurística", "metodología", "gobernanza", "escalabilidad"],
        "secuencia": ["hipótesis", "experimento", "análisis", "conclusión"],
        "num_min": 10000,
        "num_max": 99999,
        "hechos": [
            ("Aprender a aprender mejora con la práctica", True),
            ("La multitarea mejora la calidad del trabajo", False),
            ("La autorregulación emocional se puede entrenar", True),
        ],
        "pasaje": "La capacidad de adaptarse a entornos cambiantes depende de la atención, la memoria operativa y la autorregulación emocional.",
    },
}


def _opciones(textos, indice_correcta):
    """Devuelve la lista JSON de opciones para Ejercicio."""
    return [
        {"texto": t, "correcta": (i == indice_correcta)}
        for i, t in enumerate(textos)
    ]


def _build_atencion(unidad, destreza, perfil):
    """Filtrado: encontrar el intruso (un número entre palabras)."""
    nombres = perfil["animales"]
    inicio = (unidad.numero * 2) % len(nombres)
    grupo = [nombres[(inicio + i) % len(nombres)] for i in range(3)]
    intruso = str(perfil["num_min"] + unidad.numero - 1)
    return {
        "tipo": "filtrado",
        "enunciado": "Marca el elemento que NO pertenece al grupo:",
        "opciones": _opciones(grupo + [intruso], 3),
        "respuesta_correcta": "",
        "texto": "",
        "tiempo_max_seg": 60,
    }


def _build_memoria(unidad, destreza, perfil):
    """Recordar una lista y responder la posición indicada."""
    seq = perfil["secuencia"]
    pos = (unidad.numero - 1) % len(seq)
    correcta = seq[pos]
    distractores = [x for x in seq if x != correcta]
    enunciado = (
        f"Recuerda la lista: {' - '.join(seq)}. "
        f"¿Qué elemento va en la posición {pos + 1}?"
    )
    return {
        "tipo": "seleccion",
        "enunciado": enunciado,
        "opciones": _opciones(distractores + [correcta], len(distractores)),
        "respuesta_correcta": "",
        "texto": "",
        "tiempo_max_seg": 60,
    }


def _build_lectura(unidad, destreza, perfil):
    """Identificar la palabra con más letras."""
    pool = perfil["objetos"] + perfil["animales"]
    inicio = (unidad.numero * 3) % len(pool)
    candidatos = [pool[(inicio + i) % len(pool)] for i in range(4)]
    correcta = max(candidatos, key=len)
    return {
        "tipo": "seleccion",
        "enunciado": "Identifica la palabra con MAYOR número de letras:",
        "opciones": _opciones(candidatos, candidatos.index(correcta)),
        "respuesta_correcta": "",
        "texto": "",
        "tiempo_max_seg": 60,
    }


def _build_comprension(unidad, destreza, perfil):
    """Contar las oraciones del pasaje (comprensión literal objetiva)."""
    texto = perfil["pasaje"]
    oraciones = [x for x in texto.replace(". ", ".").split(".") if x.strip()]
    total = len(oraciones)
    distractores = [total - 1, total + 1, total + 2]
    indices = [total] + distractores
    return {
        "tipo": "comprension",
        "enunciado": "Según el texto, ¿cuántas oraciones lo componen?",
        "texto": texto,
        "opciones": _opciones([str(i) for i in indices], 0),
        "respuesta_correcta": "",
        "tiempo_max_seg": 90,
    }


def _build_logica(unidad, destreza, perfil):
    """Cálculo mental con rango de números del tramo."""
    a = perfil["num_min"]
    b = (unidad.numero * 3) % 10 + 1
    correcta = a + b
    opciones = [correcta, correcta + 1, correcta - 1, correcta + 2]
    return {
        "tipo": "calculo",
        "enunciado": f"Resuelve mentalmente: {a} + {b} = ?",
        "opciones": _opciones([str(x) for x in opciones], 0),
        "respuesta_correcta": "",
        "texto": "",
        "tiempo_max_seg": 45,
    }


def _build_metacognicion(unidad, destreza, perfil):
    """Verdadero/falso sobre una afirmación del tramo."""
    afirmacion, es_verdadera = perfil["hechos"][
        (unidad.numero - 1) % len(perfil["hechos"])
    ]
    return {
        "tipo": "verdadero_falso",
        "enunciado": f"Indica si la afirmación es verdadera o falsa: “{afirmacion}”",
        "opciones": _opciones(
            ["Verdadero", "Falso"], 0 if es_verdadera else 1
        ),
        "respuesta_correcta": "",
        "texto": "",
        "tiempo_max_seg": 45,
    }


BUILDERS = {
    "atencion": _build_atencion,
    "memoria": _build_memoria,
    "lectura": _build_lectura,
    "comprension": _build_comprension,
    "logica": _build_logica,
    "metacognicion": _build_metacognicion,
}


def seed_catalogo():
    """Crea el catálogo completo. Devuelve un resumen."""
    tramos = {}
    destrezas = {}

    for clave, nombre, edad_min, edad_max, orden in TRAMOS:
        tramo, _ = TramoEdad.objects.get_or_create(
            nombre=nombre,
            defaults={
                "edad_min": edad_min,
                "edad_max": edad_max,
                "orden": orden,
                "activo": True,
            },
        )
        cambios = {}
        if tramo.edad_min != edad_min:
            cambios["edad_min"] = edad_min
        if tramo.edad_max != edad_max:
            cambios["edad_max"] = edad_max
        if tramo.orden != orden:
            cambios["orden"] = orden
        if not tramo.activo:
            cambios["activo"] = True
        if cambios:
            TramoEdad.objects.filter(pk=tramo.pk).update(**cambios)
            tramo.refresh_from_db()
        tramos[clave] = tramo

        for categoria, nombre_dest, descripcion in DESTREZAS[clave]:
            destreza, _ = DestrezaCognitiva.objects.get_or_create(
                tramo=tramo,
                nombre=nombre_dest,
                defaults={
                    "categoria": categoria,
                    "descripcion": descripcion,
                    "activo": True,
                },
            )
            cambios = {}
            if destreza.categoria != categoria:
                cambios["categoria"] = categoria
            if destreza.descripcion != descripcion:
                cambios["descripcion"] = descripcion
            if not destreza.activo:
                cambios["activo"] = True
            if cambios:
                DestrezaCognitiva.objects.filter(pk=destreza.pk).update(**cambios)
                destreza.refresh_from_db()
            destrezas[(clave, categoria)] = destreza

    contador_ejercicios = 0
    for clave, tramo in tramos.items():
        perfil = PERFIL_TRAMO[clave]
        dificultad_base = DIFICULTAD_BASE[clave]
        for numero, nombre in enumerate(UNIDADES_NOMBRES, start=1):
            unidad, _ = UnidadEntrenamiento.objects.get_or_create(
                tramo=tramo,
                numero=numero,
                defaults={"nombre": nombre, "activo": True},
            )
            cambios = {}
            if unidad.nombre != nombre:
                cambios["nombre"] = nombre
            if not unidad.activo:
                cambios["activo"] = True
            if cambios:
                UnidadEntrenamiento.objects.filter(pk=unidad.pk).update(**cambios)
                unidad.refresh_from_db()

            categorias = CATEGORIAS_POR_UNIDAD[numero]
            unidad.destrezas.set([destrezas[(clave, c)] for c in categorias])

            dificultad = min(dificultad_base + numero // 4, 5)
            for categoria in categorias:
                destreza = destrezas[(clave, categoria)]
                datos = BUILDERS[categoria](unidad, destreza, perfil)
                Ejercicio.objects.update_or_create(
                    unidad=unidad,
                    destreza=destreza,
                    defaults={
                        "tipo": datos["tipo"],
                        "dificultad": dificultad,
                        "enunciado": datos["enunciado"],
                        "texto": datos["texto"],
                        "opciones": datos["opciones"],
                        "respuesta_correcta": datos["respuesta_correcta"],
                        "tiempo_max_seg": datos["tiempo_max_seg"],
                        "activo": True,
                    },
                )
                contador_ejercicios += 1

    return {
        "tramos": len(tramos),
        "destrezas": len(destrezas),
        "unidades": UnidadEntrenamiento.objects.count(),
        "ejercicios": contador_ejercicios,
    }


class Command(BaseCommand):
    help = (
        "Siembra el catálogo global del entrenamiento cognitivo "
        "(tramos, destrezas, unidades y ejercicios). Idempotente."
    )

    def handle(self, *args, **options):
        resumen = seed_catalogo()
        self.stdout.write(self.style.SUCCESS(
            "Catálogo cognitivo listo: {tramos} tramos, {destrezas} "
            "destrezas, {unidades} unidades, {ejercicios} ejercicios.".format(
                **resumen
            )
        ))
