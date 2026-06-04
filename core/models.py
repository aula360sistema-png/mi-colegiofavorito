from django.db import models

# Create your models here.
from django.db import models

class CentroEducativo(models.Model):
    nombre = models.CharField(max_length=255)
    codigo_minerd = models.CharField(max_length=50, unique=True)

    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_minerd})"

class AnioEscolar(models.Model):
    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=9)  # 2024-2025
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    activo = models.BooleanField(default=False)

    class Meta:
        unique_together = ('centro', 'nombre')

    def __str__(self):
        return f"{self.nombre} - {self.centro.nombre}"


class RolCentro(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.nombre


from usuarios.models import Usuario

class UsuarioCentro(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    centro = models.ForeignKey(CentroEducativo, on_delete=models.CASCADE)
    rol = models.ForeignKey(RolCentro, on_delete=models.PROTECT)

    activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'centro')

class ConfiguracionCentro(models.Model):
    centro = models.OneToOneField(
        CentroEducativo,
        on_delete=models.CASCADE
    )

    usa_calificacion_numerica = models.BooleanField(default=True)
    nota_minima_aprobacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70
    )
    TIPO_PAGO_CHOICES = [
        ('mensual', 'Mensual'),
        ('quincenal', 'Quincenal'),
        ('semanal', 'Semanal'),
    ]
    tipo_pago_nomina = models.CharField(
        max_length=20,
        choices=TIPO_PAGO_CHOICES,
        default='mensual'
    )
    usa_competencias = models.BooleanField(default=True)
    permite_completivo = models.BooleanField(default=True)

    modulo_asistencia = models.BooleanField(default=True)

    modulo_caja = models.BooleanField(default=False)

    modulo_nomina = models.BooleanField(default=False)

    modulo_biblioteca = models.BooleanField(default=False)

    modulo_transporte = models.BooleanField(default=False)

    modulo_cafeteria = models.BooleanField(default=False)

    modulo_inventario = models.BooleanField(default=False)

    modulo_reportes = models.BooleanField(default=True)

    modulo_mensajeria = models.BooleanField(default=False)
    permitir_qr_asistencia = models.BooleanField(default=False)

    permitir_facturacion = models.BooleanField(default=False)

    usar_biometrico = models.BooleanField(default=False)

    permitir_pago_online = models.BooleanField(default=False)

    def __str__(self):
        return f"Configuración - {self.centro.nombre}"

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    email = models.EmailField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class CentroProveedor(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    centro = models.ForeignKey(CentroEducativo, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('proveedor', 'centro')
