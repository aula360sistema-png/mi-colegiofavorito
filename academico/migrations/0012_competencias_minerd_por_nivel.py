"""Competencias MINERD por nivel.

Borra el catálogo previo (competencia sin nivel) y crea las siete
Competencias Fundamentales del currículo dominicano para cada nivel.
"""
import django.db.models.deletion
from django.db import migrations, models

# Competencias Fundamentales del currículo MINERD (Ordenanza 02-2015/03-2013).
COMPETENCIAS_MINERD = [
    "Competencia Ética y Ciudadana",
    "Competencia Comunicativa",
    "Competencia Pensamiento Lógico, Creativo y Crítico",
    "Competencia Resolución de Problemas",
    "Competencia Científica y Tecnológica",
    "Competencia Ambiental y de la Salud",
    "Competencia Desarrollo Personal y Espiritual",
]


def crear_competencias_minerd(apps, schema_editor):
    Competencia = apps.get_model("academico", "Competencia")
    Nivel = apps.get_model("academico", "Nivel")

    Competencia.objects.all().delete()

    for nivel in Nivel.objects.all().order_by("id"):
        for nombre in COMPETENCIAS_MINERD:
            Competencia.objects.create(nivel_id=nivel.id, nombre=nombre, activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0011_alter_competencia_options_competencia_activo_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_competencias_minerd),
        migrations.AlterField(
            model_name="competencia",
            name="nivel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="competencias",
                to="academico.nivel",
                verbose_name="Nivel",
            ),
        ),
    ]
