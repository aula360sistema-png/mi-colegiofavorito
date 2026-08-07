# -*- coding: utf-8 -*-
from django.db import migrations


def normalizar_estados(apps, schema_editor):
    Inscripcion = apps.get_model('estudiantes', 'Inscripcion')
    Inscripcion.objects.filter(
        estado_final='sin_calificaciones'
    ).update(estado_final='sin_calificacion')

    HistorialAcademico = apps.get_model('estudiantes', 'HistorialAcademico')
    HistorialAcademico.objects.filter(
        estado='sin_calificaciones'
    ).update(estado='sin_calificacion')


def reversa(apps, schema_editor):
    Inscripcion = apps.get_model('estudiantes', 'Inscripcion')
    Inscripcion.objects.filter(
        estado_final='sin_calificacion'
    ).update(estado_final='sin_calificaciones')

    HistorialAcademico = apps.get_model('estudiantes', 'HistorialAcademico')
    HistorialAcademico.objects.filter(
        estado='sin_calificacion'
    ).update(estado='sin_calificaciones')


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0008_alter_historialacademico_estado_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_estados, reversa),
    ]
