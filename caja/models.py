from django.db import models
from django.utils import timezone


class Caja(models.Model):
    """Caja registradora del centro. El director crea las que existirán."""
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='cajas'
    )
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('centro', 'nombre')
        ordering = ['nombre']

    @property
    def sesion_abierta(self):
        return self.sesiones.filter(estado='abierta').first()

    def __str__(self):
        return self.nombre


class ConceptoPago(models.Model):
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    nombre = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    es_recurrente = models.BooleanField(
        default=False,
        help_text="Mensual, se puede cobrar varias veces en el año"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('centro', 'nombre')
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - RD$ {self.monto:,.2f}"


class SesionCaja(models.Model):
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    caja = models.ForeignKey(
        Caja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones',
        help_text="Caja registradora sobre la que se abrió la sesión"
    )
    fecha_apertura = models.DateTimeField(default=timezone.now)
    usuario_apertura = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cajas_abiertas'
    )
    monto_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    nota_apertura = models.CharField(max_length=255, blank=True)

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='abierta'
    )

    fecha_cierre = models.DateTimeField(null=True, blank=True)
    usuario_cierre = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cajas_cerradas'
    )
    arqueo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Efectivo contado al momento del cierre"
    )
    diferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Arqueo - efectivo esperado"
    )
    nota_cierre = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-fecha_apertura']

    def total_entradas(self):
        total = self.pagos.aggregate(t=models.Sum('monto'))['t']
        return total or 0

    def total_salidas(self):
        total = self.egresos.aggregate(t=models.Sum('monto'))['t']
        return total or 0

    def saldo_esperado(self):
        return self.monto_inicial + self.total_entradas() - self.total_salidas()

    def entradas_efectivo(self):
        total = self.pagos.filter(
            metodo_pago='efectivo'
        ).aggregate(t=models.Sum('monto'))['t']
        return total or 0

    def salidas_efectivo(self):
        total = self.egresos.filter(
            metodo_pago='efectivo'
        ).aggregate(t=models.Sum('monto'))['t']
        return total or 0

    def efectivo_esperado(self):
        return self.monto_inicial + self.entradas_efectivo() - self.salidas_efectivo()

    def __str__(self):
        return f"Caja {self.id} - {self.fecha_apertura:%d/%m/%Y %H:%M}"


class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
        ('transferencia', 'Transferencia bancaria'),
        ('tarjeta', 'Tarjeta'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    sesion = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pagos'
    )
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE
    )
    concepto = models.ForeignKey(
        ConceptoPago,
        on_delete=models.PROTECT
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo'
    )
    voucher = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Código de voucher del datáfono/Verifone (pago con tarjeta)"
    )
    fecha = models.DateField(default=timezone.localdate)
    recibo = models.PositiveIntegerField(null=True, blank=True, editable=False)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

        indexes = [
            models.Index(fields=['centro', 'fecha'], name='pago_centro_fecha'),
            models.Index(fields=['estudiante'], name='pago_estudiante'),
        ]

    def __str__(self):
        return f"Recibo {self.recibo or self.id} - {self.estudiante}"


class Egreso(models.Model):
    METODO_PAGO_CHOICES = Pago.METODO_PAGO_CHOICES

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    sesion = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='egresos'
    )
    concepto = models.CharField(max_length=150)
    beneficiario = models.CharField(max_length=150, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo'
    )
    fecha = models.DateField(default=timezone.localdate)
    recibo = models.PositiveIntegerField(null=True, blank=True, editable=False)
    nota = models.CharField(max_length=255, blank=True)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

        indexes = [
            models.Index(fields=['centro', 'fecha'], name='egreso_centro_fecha'),
        ]

    def __str__(self):
        return f"Egreso {self.recibo or self.id} - RD$ {self.monto:,.2f}"


class AsignacionConcepto(models.Model):
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE
    )
    concepto = models.ForeignKey(
        ConceptoPago,
        on_delete=models.CASCADE
    )
    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.CASCADE
    )
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('estudiante', 'concepto', 'anio_escolar')
        ordering = ['estudiante__primer_apellido', 'estudiante__primer_nombre']

    def __str__(self):
        return f"{self.estudiante} - {self.concepto} ({self.anio_escolar})"
