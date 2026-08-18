from decimal import Decimal

from django.db import models
from django.utils import timezone

TASA_ITBIS = Decimal('0.18')


class TipoComprobante(models.Model):
    """Catálogo de comprobantes fiscales electrónicos (e-CF) según la DGII (Rep. Dominicana)."""
    codigo = models.CharField(max_length=2, unique=True)
    nombre = models.CharField(max_length=120)
    letra = models.CharField(
        max_length=2,
        help_text="Serie del e-NCF: siempre E en comprobantes electrónicos"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Tipo de comprobante'
        verbose_name_plural = 'Tipos de comprobante'

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class SecuenciaNCF(models.Model):
    """Secuencia por centro y tipo de comprobante para generar e-NCF."""
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='secuencias_ncf'
    )
    tipo = models.ForeignKey(
        TipoComprobante,
        on_delete=models.PROTECT
    )
    ultimo_numero = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('centro', 'tipo')
        verbose_name = 'Secuencia NCF'
        verbose_name_plural = 'Secuencias NCF'

    def __str__(self):
        return f"{self.tipo.nombre} @ {self.centro.nombre} → {self.ultimo_numero}"


class Factura(models.Model):
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='facturas'
    )
    ncf = models.CharField(
        max_length=20,
        blank=True,
        help_text="Número de comprobante fiscal electrónico (e-NCF); vacío si no aplica"
    )
    tipo = models.ForeignKey(
        TipoComprobante,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    pago = models.OneToOneField(
        'caja.Pago',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='factura',
        help_text="Pago de caja que origina esta factura"
    )
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='facturas'
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aplica_itbis = models.BooleanField(
        default=False,
        help_text="Indica si la factura desglosa ITBIS (18%)"
    )
    fecha = models.DateField(default=timezone.localdate)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        constraints = [
            models.UniqueConstraint(
                fields=['centro', 'ncf'],
                condition=models.Q(ncf__gt=''),
                name='unique_ncf_por_centro'
            )
        ]

    @property
    def numero_legible(self):
        return self.ncf or f"R-{self.pago.recibo if self.pago else self.id}"

    @property
    def total_items(self):
        return self.items.aggregate(t=models.Sum('subtotal'))['t'] or 0

    def __str__(self):
        return f"Factura {self.numero_legible} · {self.estudiante} · RD$ {self.total:,.2f}"


class FacturaItem(models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='items'
    )
    concepto = models.ForeignKey(
        'caja.ConceptoPago',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    descripcion = models.CharField(max_length=200)
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.descripcion} × {self.cantidad}"
