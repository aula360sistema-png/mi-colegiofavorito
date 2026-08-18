"""Normaliza el catálogo de competencias a las 4 definidas por el centro.

Mantiene (creándolas si falta) las cuatro competencias especificadas por el
centro para la calificación y desactiva el resto (las siete Competencias
Fundamentales de la migración 0012). Las competencias desactivadas se
conservan por si hay calificaciones históricas que las referencien.
"""
from django.db import migrations

# Las cuatro competencias con las que se califica (orden 1 a 4).
COMPETENCIAS_CUATRO = [
    ("Competencia Comunicativa", 1),
    (
        "Competencia Pensamiento Lógico, Creativo y Crítico y "
        "Resolución de Problemas",
        2,
    ),
    (
        "Competencia Científica y Tecnológica y Ambiental y de la Salud",
        3,
    ),
    (
        "Competencia Ética y Ciudadana y Desarrollo Personal y Espiritual",
        4,
    ),
]


def normalizar_cuatro_competencias(apps, schema_editor):
    Competencia = apps.get_model("academico", "Competencia")
    Nivel = apps.get_model("academico", "Nivel")

    nombres = [nombre for nombre, _ in COMPETENCIAS_CUATRO]

    for nivel in Nivel.objects.all():
        for nombre, orden in COMPETENCIAS_CUATRO:
            competencia, _ = Competencia.objects.get_or_create(
                nivel=nivel,
                nombre=nombre,
                defaults={"activo": True, "orden": orden},
            )
            if not competencia.activo or competencia.orden != orden:
                competencia.activo = True
                competencia.orden = orden
                competencia.save(update_fields=["activo", "orden"])

        Competencia.objects.filter(
            nivel=nivel,
        ).exclude(
            nombre__in=nombres,
        ).update(activo=False)


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0017_calificacion_cal_inscripcion_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_cuatro_competencias, revertir),
    ]
