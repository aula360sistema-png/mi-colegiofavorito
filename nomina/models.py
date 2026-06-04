from django.db import models

from core.models import CentroEducativo
from usuarios.models import Usuario


# =====================================================
# AFP
# =====================================================

class AFP(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    porcentaje_empleado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.87
    )

    porcentaje_empresa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=7.10
    )

    activo = models.BooleanField(
        default=True
    )

    def __str__(self):

        return self.nombre


# =====================================================
# ARS
# =====================================================

class ARS(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    porcentaje_empleado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.04
    )

    porcentaje_empresa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=7.09
    )

    activo = models.BooleanField(
        default=True
    )

    def __str__(self):

        return self.nombre


# =====================================================
# CARGOS
# =====================================================

class Cargo(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    descripcion = models.TextField(
        blank=True
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['nombre']

    def __str__(self):

        return self.nombre


# =====================================================
# CONFIGURACION NOMINA EMPLEADO
# =====================================================

class ConfiguracionNomina(models.Model):

    TIPOS_PAGO = (
        ('mensual', 'Mensual'),
        ('quincenal', 'Quincenal'),
        ('semanal', 'Semanal'),
    )

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='configuracion_nomina'
    )

    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.CASCADE
    )

    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    salario_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    afp = models.ForeignKey(
        AFP,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    ars = models.ForeignKey(
        ARS,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    tipo_pago = models.CharField(
        max_length=20,
        choices=TIPOS_PAGO,
        default='mensual'
    )

    activo_nomina = models.BooleanField(
        default=True
    )

    cuenta_bancaria = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    fecha_ingreso = models.DateField(
        blank=True,
        null=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ['usuario']

    def __str__(self):

        return f"{self.usuario}"


# =====================================================
# TIPOS DE INGRESOS
# =====================================================

class TipoIngreso(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    obligatorio = models.BooleanField(
        default=False
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['nombre']

    def __str__(self):

        return self.nombre


# =====================================================
# TIPOS DE DESCUENTOS
# =====================================================

class TipoDescuento(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    es_porcentaje = models.BooleanField(
        default=True
    )

    obligatorio = models.BooleanField(
        default=False
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['nombre']

    def __str__(self):

        return self.nombre


# =====================================================
# INGRESOS FIJOS EMPLEADO
# =====================================================

class IngresoEmpleado(models.Model):

    configuracion = models.ForeignKey(
        ConfiguracionNomina,
        on_delete=models.CASCADE,
        related_name='ingresos_fijos'
    )

    tipo = models.ForeignKey(
        TipoIngreso,
        on_delete=models.PROTECT
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.configuracion} - {self.tipo}"


# =====================================================
# DESCUENTOS FIJOS EMPLEADO
# =====================================================

class DescuentoEmpleado(models.Model):

    configuracion = models.ForeignKey(
        ConfiguracionNomina,
        on_delete=models.CASCADE,
        related_name='descuentos_fijos'
    )

    tipo = models.ForeignKey(
        TipoDescuento,
        on_delete=models.PROTECT
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.configuracion} - {self.tipo}"


# =====================================================
# PERIODOS DE NOMINA
# =====================================================

class PeriodoNomina(models.Model):

    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.CASCADE
    )

    anio = models.IntegerField()

    mes = models.IntegerField()

    numero_periodo = models.IntegerField(
        default=1
    )

    descripcion = models.CharField(
        max_length=150
    )

    fecha_inicio = models.DateField()

    fecha_fin = models.DateField()

    fecha_pago = models.DateField()

    cerrado = models.BooleanField(
        default=False
    )

    nomina_generada = models.BooleanField(
        default=False
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            '-anio',
            '-mes',
            '-numero_periodo'
        ]

        unique_together = (
            'centro',
            'anio',
            'mes',
            'numero_periodo'
        )

    def __str__(self):

        return f"{self.descripcion}"


# =====================================================
# NOMINA GENERADA
# =====================================================

class Nomina(models.Model):

    ESTADOS = (
        ('GENERADA', 'Generada'),
        ('REVISADA', 'Revisada'),
        ('APROBADA', 'Aprobada'),
        ('PAGADA', 'Pagada'),
        ('ANULADA', 'Anulada'),
    )

    periodo = models.ForeignKey(
        PeriodoNomina,
        on_delete=models.CASCADE
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    configuracion = models.ForeignKey(
        ConfiguracionNomina,
        on_delete=models.CASCADE
    )

    salario_base = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_ingresos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_descuentos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    neto_pagar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='GENERADA'
    )

    pagado = models.BooleanField(
        default=False
    )

    fecha_pago = models.DateField(
        blank=True,
        null=True
    )

    generado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='nominas_generadas'
    )

    fecha_generacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'periodo',
            'usuario'
        )

    def __str__(self):

        return f"{self.usuario} - {self.periodo}"


# =====================================================
# DETALLE INGRESOS NOMINA
# =====================================================

class IngresoNomina(models.Model):

    nomina = models.ForeignKey(
        Nomina,
        on_delete=models.CASCADE,
        related_name='ingresos'
    )

    tipo = models.ForeignKey(
        TipoIngreso,
        on_delete=models.PROTECT
    )

    descripcion = models.CharField(
        max_length=150
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):

        return f"{self.tipo} - {self.monto}"


# =====================================================
# DETALLE DESCUENTOS NOMINA
# =====================================================

class DescuentoNomina(models.Model):

    nomina = models.ForeignKey(
        Nomina,
        on_delete=models.CASCADE,
        related_name='descuentos'
    )

    tipo = models.ForeignKey(
        TipoDescuento,
        on_delete=models.PROTECT
    )

    descripcion = models.CharField(
        max_length=150
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):

        return f"{self.tipo} - {self.monto}"