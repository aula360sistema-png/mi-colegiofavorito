from django.db import migrations, models


NIVELES_MINERD = {
    'inicial': 'Nivel Inicial',
    'primaria': 'Nivel Primario',
    'secundaria': 'Nivel Secundario',
}

GRADOS_POR_TIPO = {
    'inicial': [
        'Maternal', 'Infantes', 'Párvulos',
        'Pre-Kínder', 'Kínder', 'Preprimario',
    ],
    'primaria': [
        '1ro de Primaria', '2do de Primaria', '3ro de Primaria',
        '4to de Primaria', '5to de Primaria', '6to de Primaria',
    ],
    'secundaria': [
        '1ro de Secundaria', '2do de Secundaria', '3ro de Secundaria',
        '4to de Secundaria', '5to de Secundaria', '6to de Secundaria',
    ],
}


def _estructura_minerd(apps, schema_editor):
    """Normaliza la estructura a la oficial del currículo MINERD.

    - Renombra los niveles a su nombre oficial según tipo.
    - Deduplica niveles repetidos (centro, tipo) re-apuntando Grado.nivel.
    - Renombra los grados por tipo según su orden y asigna el ciclo (1/2).
    - Deduplica grados repetidos (nivel, nombre) re-apuntando FK y M2M.
    """
    Nivel = apps.get_model('academico', 'Nivel')
    Grado = apps.get_model('academico', 'Grado')
    Inscripcion = apps.get_model('estudiantes', 'Inscripcion')
    HistorialAcademico = apps.get_model('estudiantes', 'HistorialAcademico')
    DocenteMateria = apps.get_model('academico', 'DocenteMateria')
    GradoAsignatura = apps.get_model('academico', 'GradoAsignatura')
    AsignacionDocente = apps.get_model('docentes', 'AsignacionDocente')
    Acta = apps.get_model('administracion', 'Acta')

    # 1) Niveles: nombre oficial por tipo
    for nivel in Nivel.objects.all():
        oficial = NIVELES_MINERD.get(nivel.tipo)
        if oficial and nivel.nombre != oficial:
            nivel.nombre = oficial
            nivel.save(update_fields=['nombre'])

    # 2) Deduplicar niveles (centro, tipo)
    pares = Nivel.objects.values_list('centro_id', 'tipo').distinct()
    for centro_id, tipo in pares:
        niveles = list(
            Nivel.objects.filter(centro_id=centro_id, tipo=tipo).order_by('id')
        )
        if len(niveles) <= 1:
            continue
        canonica, dups = niveles[0], niveles[1:]
        for dup in dups:
            Grado.objects.filter(nivel=dup).update(nivel=canonica)
            dup.delete()

    # 3) Grados: renombrar por tipo (según orden) y fijar ciclo
    for tipo, nombres in GRADOS_POR_TIPO.items():
        for nivel in Nivel.objects.filter(tipo=tipo):
            grados = list(
                Grado.objects.filter(nivel=nivel).order_by('orden', 'id')
            )
            for idx, grado in enumerate(grados):
                if idx < len(nombres):
                    grado.nombre = nombres[idx]
                grado.ciclo = 1 if idx < 3 else 2
                grado.save(update_fields=['nombre', 'ciclo'])

    # 4) Deduplicar grados (nivel, nombre)
    pares = Grado.objects.values_list('nivel_id', 'nombre').distinct()
    for nivel_id, nombre in pares:
        grados = list(
            Grado.objects.filter(nivel_id=nivel_id, nombre=nombre).order_by('id')
        )
        if len(grados) <= 1:
            continue
        canonica, dups = grados[0], grados[1:]
        for dup in dups:
            for seccion in dup.secciones.all():
                canonica.secciones.add(seccion)
            Inscripcion.objects.filter(grado=dup).update(grado=canonica)
            HistorialAcademico.objects.filter(grado=dup).update(grado=canonica)
            DocenteMateria.objects.filter(grado=dup).update(grado=canonica)
            GradoAsignatura.objects.filter(grado=dup).update(grado=canonica)
            AsignacionDocente.objects.filter(grado=dup).update(grado=canonica)
            Acta.objects.filter(grado=dup).update(grado=canonica)
            dup.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0009_seccion_global_unica'),
        ('core', '0007_configuracioncentro_facturacion_itbis_and_more'),
        ('estudiantes', '0012_alter_estudiante_modalidad_salida'),
        ('docentes', '0002_initial'),
        ('administracion', '0004_alter_administrativo_cargo'),
    ]

    operations = [
        migrations.AddField(
            model_name='grado',
            name='ciclo',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Ciclo del nivel según el currículo MINERD (1 o 2).',
            ),
        ),
        migrations.RunPython(_estructura_minerd, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='nivel',
            unique_together={('centro', 'tipo')},
        ),
        migrations.AlterUniqueTogether(
            name='grado',
            unique_together={('nivel', 'nombre')},
        ),
    ]
