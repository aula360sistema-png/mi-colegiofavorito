import django.db.models.deletion
from django.db import migrations, models


def _migrar_catalogo_periodos(apps, schema_editor):
    """Convierte los períodos por año en un catálogo reutilizable.

    - El primer período de cada (centro, nombre) pasa a ser el catálogo.
    - Se crea un PeriodoAnio por cada (período, año escolar) con su estado.
    - Las calificaciones se remapean del período duplicado al del catálogo.
    """
    Periodo = apps.get_model('academico', 'Periodo')
    PeriodoAnio = apps.get_model('academico', 'PeriodoAnio')
    Calificacion = apps.get_model('academico', 'Calificacion')

    vistos = {}
    for p in Periodo.objects.all().order_by('id'):
        clave = (p.centro_id, p.nombre.lower())
        vistos.setdefault(clave, p)

    catalogo_ids = {p.id for p in vistos.values()}

    for p in Periodo.objects.all().order_by('id'):
        if p.id not in catalogo_ids:
            cat = vistos[(p.centro_id, p.nombre.lower())]
            Calificacion.objects.filter(periodo_id=p.id).update(periodo_id=cat.id)
        else:
            cat = p

        PeriodoAnio.objects.get_or_create(
            periodo_id=cat.id,
            anio_escolar_id=p.anio_escolar_id,
            defaults={
                'activo': p.activo,
                'cerrado': p.cerrado,
                'fecha_cierre': p.fecha_cierre,
            }
        )

        if p.id != cat.id:
            p.delete()


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0012_competencias_minerd_por_nivel'),
        ('core', '0007_configuracioncentro_facturacion_itbis_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PeriodoAnio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True)),
                ('cerrado', models.BooleanField(default=False)),
                ('fecha_cierre', models.DateField(blank=True, null=True)),
                ('anio_escolar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='periodos_estado', to='core.anioescolar')),
                ('periodo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estados', to='academico.periodo')),
            ],
            options={
                'ordering': ['periodo__orden', 'periodo__nombre'],
                'unique_together': {('periodo', 'anio_escolar')},
            },
        ),
        migrations.RunPython(_migrar_catalogo_periodos, _noop),
        migrations.AlterModelOptions(
            name='periodo',
            options={'ordering': ['orden', 'nombre']},
        ),
        migrations.AlterUniqueTogether(
            name='periodo',
            unique_together={('centro', 'nombre')},
        ),
        migrations.RemoveField(
            model_name='periodo',
            name='activo',
        ),
        migrations.RemoveField(
            model_name='periodo',
            name='anio_escolar',
        ),
        migrations.RemoveField(
            model_name='periodo',
            name='cerrado',
        ),
        migrations.RemoveField(
            model_name='periodo',
            name='fecha_cierre',
        ),
    ]
