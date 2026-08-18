from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
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
    cerrado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('centro', 'nombre')

        indexes = [
            models.Index(fields=['centro', 'activo'], name='anio_centro_activo'),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['centro'],
                condition=models.Q(activo=True),
                name='unique_active_year_per_center'
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.centro.nombre}"
    
    def cerrar(self):
        self.cerrado = True
        self.activo = False
        self.save()
    
    def save(self, *args, **kwargs):

        if self.activo:

            # Si se activa un año, automáticamente se abre
            self.cerrado = False

            # Cerrar los demás
            AnioEscolar.objects.filter(
                centro=self.centro,
                activo=True
            ).exclude(
                id=self.id
            ).update(
                activo=False,
                cerrado=True
            )

        super().save(*args, **kwargs)
    
  

   # def clean(self):
    #    if self.cerrado and self.activo:
   #         raise ValidationError({
   #             'activo': 'Un año escolar cerrado no puede activarse.'
  #          })
   


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

    rnc = models.CharField(
        max_length=11,
        blank=True,
        help_text="RNC del centro para las facturas fiscales"
    )
    facturacion_itbis = models.BooleanField(
        default=False,
        help_text="Activa el desglose de ITBIS (18%) en las facturas"
    )

    usar_biometrico = models.BooleanField(default=False)

    permitir_pago_online = models.BooleanField(default=False)

    modulo_certificados = models.BooleanField(
        default=False,
        help_text="Activa las solicitudes de certificados/constancias en línea"
    )
    precio_certificado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Costo de cada certificado/constancia solicitado"
    )

    # ------------------------------------------------------------------
    # Correo y WhatsApp (módulo de comunicaciones)
    # ------------------------------------------------------------------
    # Valores por centro. Si quedan vacíos se usa lo configurado en
    # settings/.env (y si tampoco hay SMTP, se usa el backend de consola).
    email_servidor = models.CharField(
        'Servidor SMTP',
        max_length=200,
        blank=True,
        default='',
        help_text="Ej: smtp.gmail.com"
    )
    email_puerto = models.PositiveIntegerField(
        'Puerto SMTP',
        default=587,
        help_text="587 (TLS) o 465 (SSL)"
    )
    email_usuario = models.CharField(
        'Usuario de correo',
        max_length=200,
        blank=True,
        default=''
    )
    email_clave = models.CharField(
        'Contraseña / clave de aplicación (app password)',
        max_length=300,
        blank=True,
        default='',
        help_text=(
            "Gmail/Outlook: usa una 'clave de aplicación' (app password) "
            "generada en la cuenta, NO la contraseña normal. Ej: xxxx xxxx "
            "xxxx xxxx"
        ),
    )
    email_tls = models.BooleanField(
        'Usar TLS',
        default=True,
        help_text="Conexión segura TLS (puerto 587). Quitar si usas SSL (465)."
    )
    email_ssl = models.BooleanField(
        'Usar SSL',
        default=False,
        help_text="Conexión segura SSL (puerto 465)."
    )
    email_remitente = models.EmailField(
        'Correo remitente (From)',
        blank=True,
        default='',
        help_text="Dirección desde la que llegan los correos."
    )

    whatsapp_url = models.CharField(
        'URL del gateway WhatsApp',
        max_length=300,
        blank=True,
        default='',
        help_text="Endpoint que recibe el POST JSON (Twilio, Meta Cloud API, etc.)."
    )
    whatsapp_token = models.CharField(
        'Token del gateway WhatsApp',
        max_length=300,
        blank=True,
        default=''
    )
    whatsapp_remitente = models.CharField(
        'Remitente WhatsApp (from)',
        max_length=100,
        blank=True,
        default='',
        help_text="Opcional. Número o ID del remitente que envía los mensajes."
    )

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
