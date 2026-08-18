import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count


def _seccion_global(apps, schema_editor):
    """Convierte secciones por grado en un catálogo único por centro.

    - Pobla Seccion.centro desde grado.nivel.centro.
    - Registra en Grado.secciones (M2M) las secciones que cada grado usaba.
    - Deduplica las secciones repetidas (misma letra + mismo centro) y
      re-apunta todos los FK (Inscripcion, HistorialAcademico,
      DocenteMateria, AsignacionDocente) a la sección canónica.
    """
    Seccion = apps.get_model('academico', 'Seccion')
    Inscripcion = apps.get_model('estudiantes', 'Inscripcion')
    HistorialAcademico = apps.get_model('estudiantes', 'HistorialAcademico')
    DocenteMateria = apps.get_model('academico', 'DocenteMateria')
    AsignacionDocente = apps.get_model('docentes', 'AsignacionDocente')

    for seccion in Seccion.objects.select_related('grado__nivel').all():
        if seccion.grado_id is not None:
            seccion.centro_id = seccion.grado.nivel.centro_id
            seccion.save(update_fields=['centro_id'])
            seccion.grado.secciones.add(seccion)

    grupos = (
        Seccion.objects
        .values('centro_id', 'nombre')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    for grupo in grupos:
        canonicas = Seccion.objects.filter(
            centro_id=grupo['centro_id'],
            nombre=grupo['nombre'],
        ).order_by('id')
        canonica = canonicas.first()
        duplicadas = canonicas.exclude(pk=canonica.pk)

        for dup in duplicadas:
            if dup.grado_id is not None:
                dup.grado.secciones.add(canonica)

            Inscripcion.objects.filter(seccion=dup).update(seccion=canonica)
            HistorialAcademico.objects.filter(seccion=dup).update(seccion=canonica)
            DocenteMateria.objects.filter(seccion=dup).update(seccion=canonica)
            AsignacionDocente.objects.filter(seccion=dup).update(seccion=canonica)

            dup.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0008_nivel_tipo'),
        ('core', '0007_configuracioncentro_facturacion_itbis_and_more'),
        ('estudiantes', '0012_alter_estudiante_modalidad_salida'),
        ('docentes', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='seccion',
            name='centro',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='core.centroeducativo',
            ),
        ),
        migrations.AddField(
            model_name='grado',
            name='secciones',
            field=models.ManyToManyField(
                blank=True,
                help_text='Secciones que usa este grado (ej: A, B, C).',
                related_name='grados',
                to='academico.seccion',
            ),
        ),
        migrations.RunPython(_seccion_global, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='seccion',
            name='centro',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='core.centroeducativo',
            ),
        ),
        migrations.AlterModelOptions(
            name='seccion',
            options={'ordering': ['nombre']},
        ),
        migrations.AlterUniqueTogether(
            name='seccion',
            unique_together={('centro', 'nombre')},
        ),
        migrations.RemoveField(
            model_name='seccion',
            name='grado',
        ),
    ]
