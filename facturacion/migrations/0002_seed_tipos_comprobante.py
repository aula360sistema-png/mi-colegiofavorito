from django.db import migrations

TIPOS_DGII = [
    ('01', 'Crédito Fiscal', 'A'),
    ('02', 'Consumo', 'B'),
    ('03', 'Débito Fiscal', 'C'),
    ('04', 'Gubernamental', 'D'),
    ('05', 'Especial', 'E'),
    ('06', 'Pago al exterior', 'F'),
    ('07', 'Regímenes especiales de facturación', 'G'),
    ('08', 'Venta exclusiva zonas francas', 'H'),
    ('09', 'Venta inmuebles concesionarios', 'I'),
    ('10', 'Gastos menores', 'J'),
    ('11', 'Ingresos', 'K'),
    ('12', 'Gastos y compras del Estado', 'L'),
    ('13', 'Comprobante gubernamental', 'M'),
    ('14', 'Comprobante para afiliados', 'N'),
    ('15', 'Comprobante para turistas', 'O'),
    ('16', 'Venta a concesionarios', 'P'),
    ('17', 'Contratos en subasta', 'Q'),
    ('18', 'Contratos en subasta zona franca', 'R'),
    ('19', 'Venta internacional', 'S'),
    ('20', 'Ingresos a operaciones de póliza', 'T'),
    ('21', 'Egresos de operaciones de póliza', 'U'),
    ('22', 'Pago al exterior (pólizas)', 'V'),
    ('23', 'Nota de crédito (solo crédito fiscal)', 'W'),
    ('24', 'Nota de débito', 'X'),
    ('25', 'Nota de crédito (consumo)', 'Y'),
    ('26', 'Nota de débito (consumo)', 'Z'),
    ('27', 'Comprobante gubernamental', 'AA'),
    ('28', 'Nota de crédito (gubernamental)', 'AB'),
    ('29', 'Nota de débito (gubernamental)', 'AC'),
    ('30', 'Comprobante para gastos menores', 'AD'),
    ('31', 'Nota de crédito (gastos menores)', 'AE'),
    ('32', 'Nota de débito (gastos menores)', 'AF'),
    ('33', 'Comprobante de regímenes especiales', 'AG'),
    ('34', 'Nota de crédito (regímenes especiales)', 'AH'),
    ('35', 'Nota de débito (regímenes especiales)', 'AI'),
    ('36', 'Comprobante de exportación', 'AJ'),
    ('37', 'Nota de crédito (exportación)', 'AK'),
    ('38', 'Nota de débito (exportación)', 'AL'),
    ('39', 'Comprobante de proveedores informales', 'AM'),
    ('40', 'Nota de crédito (proveedores informales)', 'AN'),
    ('41', 'Nota de débito (proveedores informales)', 'AO'),
    ('42', 'Comprobante para pagos al exterior', 'AP'),
    ('43', 'Nota de crédito (pagos al exterior)', 'AQ'),
    ('44', 'Nota de débito (pagos al exterior)', 'AR'),
    ('45', 'Nota de crédito (regímenes especiales)', 'AS'),
]


def seed_tipos(apps, schema_editor):
    TipoComprobante = apps.get_model('facturacion', 'TipoComprobante')
    for codigo, nombre, letra in TIPOS_DGII:
        TipoComprobante.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'letra': letra,
                'activo': codigo in ('01', '02'),
            },
        )


def unseed_tipos(apps, schema_editor):
    TipoComprobante = apps.get_model('facturacion', 'TipoComprobante')
    TipoComprobante.objects.filter(
        codigo__in=[c for c, _, _ in TIPOS_DGII]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_tipos, unseed_tipos),
    ]
