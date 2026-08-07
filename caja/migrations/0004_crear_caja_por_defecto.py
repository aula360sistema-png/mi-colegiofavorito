from django.db import migrations


def crear_caja_por_defecto(apps, schema_editor):
    CentroEducativo = apps.get_model('core', 'CentroEducativo')
    Caja = apps.get_model('caja', 'Caja')
    SesionCaja = apps.get_model('caja', 'SesionCaja')

    for centro in CentroEducativo.objects.all():
        caja = Caja.objects.filter(centro=centro).first()
        if not caja:
            caja = Caja.objects.create(
                centro=centro,
                nombre='Caja Principal',
                activa=True,
            )
        SesionCaja.objects.filter(
            centro=centro,
            caja__isnull=True,
        ).update(caja=caja)


class Migration(migrations.Migration):

    dependencies = [
        ('caja', '0003_caja_sesioncaja_caja'),
    ]

    operations = [
        migrations.RunPython(
            crear_caja_por_defecto,
            migrations.RunPython.noop,
        ),
    ]
