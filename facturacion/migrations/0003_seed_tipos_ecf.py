from django.db import migrations

TIPOS_ECF = [
    ('31', 'Factura de Crédito Fiscal Electrónica'),
    ('32', 'Factura de Consumo Electrónica'),
    ('33', 'Nota de Débito Electrónica'),
    ('34', 'Nota de Crédito Electrónica'),
    ('41', 'Comprobante Electrónico de Compras'),
    ('43', 'Comprobante Electrónico para Gastos Menores'),
    ('44', 'Comprobante Electrónico para Regímenes Especiales'),
    ('45', 'Comprobante Electrónico Gubernamental'),
    ('46', 'Comprobante Electrónico para Exportaciones'),
    ('47', 'Comprobante Electrónico para Pagos al Exterior'),
]


def seed_ecf(apps, schema_editor):
    TipoComprobante = apps.get_model('facturacion', 'TipoComprobante')
    SecuenciaNCF = apps.get_model('facturacion', 'SecuenciaNCF')
    Factura = apps.get_model('facturacion', 'Factura')

    # Reemplaza los tipos físicos (NCF en papel) por los electrónicos (e-CF)
    antiguos = TipoComprobante.objects.exclude(
        codigo__in=[codigo for codigo, _ in TIPOS_ECF]
    )
    SecuenciaNCF.objects.filter(tipo__in=antiguos).delete()
    Factura.objects.filter(tipo__in=antiguos).update(tipo=None)
    antiguos.delete()

    for codigo, nombre in TIPOS_ECF:
        TipoComprobante.objects.update_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'letra': 'E',
                'activo': codigo in ('31', '32'),
            },
        )


def unseed_ecf(apps, schema_editor):
    TipoComprobante = apps.get_model('facturacion', 'TipoComprobante')
    SecuenciaNCF = apps.get_model('facturacion', 'SecuenciaNCF')
    Factura = apps.get_model('facturacion', 'Factura')

    nuevos = TipoComprobante.objects.filter(
        codigo__in=[codigo for codigo, _ in TIPOS_ECF]
    )
    SecuenciaNCF.objects.filter(tipo__in=nuevos).delete()
    Factura.objects.filter(tipo__in=nuevos).update(tipo=None)
    nuevos.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0002_seed_tipos_comprobante'),
    ]

    operations = [
        migrations.RunPython(seed_ecf, unseed_ecf),
    ]
