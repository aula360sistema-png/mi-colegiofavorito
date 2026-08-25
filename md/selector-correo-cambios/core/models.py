from django.db import models
from django.core.exceptions import ValidationError


class CentroEducativo(models.Model):
    nombre = models.CharField(max_length=255)
    codigo_minerd = models.CharField(max_length=50, unique=True)

    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    logo = models.ImageField(
        upload_to='centros/logos/',
        blank=True,
        null=True,
        help_text='Logo del centro educativo (se muestra en sidebar, login, PDFs)'
    )

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


class CierreAnio(models.Model):
    """Bitácora oficial del cierre de un año escolar.

    Deja constancia de quién cerró, cuándo, con qué resumen de
    resultados y qué deudas quedaron pendientes. También registra
    reaperturas supervisadas.
    """

    anio_escolar = models.OneToOneField(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='cierre'
    )

    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='cierres_realizados'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    # {'inscritos': n, 'aprobados': n, 'reprobados': n, ...}
    totales = models.JSONField(default=dict)
    # [{'matricula','nombre','grado','saldo'}]
    deudores = models.JSONField(default=list)
    total_deuda = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    reabierto = models.BooleanField(default=False)
    motivo_reapertura = models.TextField(blank=True)
    usuario_reapertura = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reaperturas_realizadas'
    )
    fecha_reapertura = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Cierre {self.anio_escolar.nombre} ({'reabierto' if self.reabierto else 'cerrado'})"


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
    PROVEEDORES_CORREO = (
        ('smtp_gmail', 'Gmail / Google Workspace (SMTP)'),
        ('smtp_outlook', 'Outlook / Microsoft 365 (SMTP)'),
        ('smtp_otro', 'Otro servidor SMTP (personalizado)'),
        ('resend', 'Resend (API)'),
        ('sendgrid', 'SendGrid (API)'),
        ('consola', 'Ninguno (modo consola / desarrollo)'),
    )

    email_proveedor = models.CharField(
        'Proveedor de correo',
        max_length=20,
        choices=PROVEEDORES_CORREO,
        default='consola',
        help_text=(
            "Elige cómo se envían los correos de este centro. Si tu "
            "hosting bloquea SMTP (ej. Render plan gratuito), usa Resend "
            "o SendGrid."
        ),
    )
    email_api_key = models.CharField(
        'API Key del proveedor',
        max_length=300,
        blank=True,
        default='',
        help_text='API Key de Resend o SendGrid, según el proveedor elegido.',
    )
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


# =====================================================
# PERMISOS POR PAGINA
# =====================================================

class PermisoPagina(models.Model):
    """Controla qué roles pueden acceder a cada página (URL name).

    Si no existe un registro para una URL, la página queda abierta a todos
    los usuarios autenticados (comportamiento actual). Si se crea un
    registro, solo los roles/usuarios listados pueden acceder.
    """

    url_name = models.CharField(
        max_length=150,
        unique=True,
        help_text='Nombre de la URL en Django (ej: estudiante_list, nomina:dashboard)'
    )
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Descripción legible de la página'
    )
    roles_permitidos = models.ManyToManyField(
        RolCentro,
        blank=True,
        related_name='permisos_pagina',
        help_text='Roles que pueden acceder a esta página'
    )
    usuarios_permitidos = models.ManyToManyField(
        'usuarios.Usuario',
        blank=True,
        related_name='permisos_pagina_directos',
        help_text='Usuarios individuales con acceso (además de los roles)'
    )
    activo = models.BooleanField(
        default=True,
        help_text='Si está inactivo, la regla no se aplica'
    )

    class Meta:
        ordering = ['url_name']
        verbose_name = 'Permiso de página'
        verbose_name_plural = 'Permisos de página'

    def __str__(self):
        return f"{self.url_name} → {', '.join(r.nombre for r in self.roles_permitidos.all()) or 'sin roles'}"


# =====================================================
# TEMA / APARIENCIA POR CENTRO
# =====================================================

class TemaCentro(models.Model):
    """Colores personalizables del UI para cada centro educativo.

    Se almacenan como hex (#RRGGBB) y se inyectan al CSS vía
    un style tag en home.html o un context processor.
    """

    centro = models.OneToOneField(
        CentroEducativo,
        on_delete=models.CASCADE,
        related_name='tema'
    )

    nombre = models.CharField(
        max_length=50,
        default='Por defecto',
        help_text='Nombre del tema (ej: Azul, Verde, Morado)'
    )

    color_primario = models.CharField(
        max_length=7,
        default='#4f46e5',
        help_text='Color principal (sidebar, botones, headers)'
    )
    color_secundario = models.CharField(
        max_length=7,
        default='#6366f1',
        help_text='Color secundario (hover, acentos)'
    )
    color_acento = models.CharField(
        max_length=7,
        default='#818cf8',
        help_text='Color de acento (secciones, badges)'
    )
    color_texto = models.CharField(
        max_length=7,
        default='#111827',
        help_text='Color del texto principal'
    )
    color_fondo = models.CharField(
        max_length=7,
        default='#f5f7fb',
        help_text='Color de fondo del body'
    )
    color_fondo_sidebar = models.CharField(
        max_length=7,
        default='#312e81',
        help_text='Color de fondo del sidebar'
    )
    color_texto_sidebar = models.CharField(
        max_length=7,
        default='#c7d2fe',
        help_text='Color del texto en el sidebar'
    )
    color_borde = models.CharField(
        max_length=7,
        default='#e5e7eb',
        help_text='Color de bordes y separadores'
    )

    color_peligro = models.CharField(
        max_length=7,
        default='#dc2626',
        help_text='Color para errores, danger, alertas rojas'
    )
    color_exito = models.CharField(
        max_length=7,
        default='#16a34a',
        help_text='Color para éxito, badges verdes, pagos'
    )
    color_advertencia = models.CharField(
        max_length=7,
        default='#f59e0b',
        help_text='Color para advertencias, warnings amarillos'
    )

    class Meta:
        verbose_name = 'Tema del centro'
        verbose_name_plural = 'Temas de centros'

    def __str__(self):
        return f"Tema {self.nombre} — {self.centro.nombre}"

    def to_css_variables(self):
        """Devuelve el CSS con las variables definidas."""
        return (
            f":root {{\n"
            f"  --color-primary: {self.color_primario};\n"
            f"  --color-secondary: {self.color_secundario};\n"
            f"  --color-accent: {self.color_acento};\n"
            f"  --color-text: {self.color_texto};\n"
            f"  --color-bg: {self.color_fondo};\n"
            f"  --color-sidebar-bg: {self.color_fondo_sidebar};\n"
            f"  --color-sidebar-text: {self.color_texto_sidebar};\n"
            f"  --color-border: {self.color_borde};\n"
            f"  --color-danger: {self.color_peligro};\n"
            f"  --color-success: {self.color_exito};\n"
            f"  --color-warning: {self.color_advertencia};\n"
            f"}}"
        )


# =====================================================
# SEMILLA DE TEMAS PREDEFINIDOS
# =====================================================

TEMAS_PREDEFINIDOS = [
    {
        'nombre': 'Índigo',
        'color_primario': '#4f46e5',
        'color_secundario': '#6366f1',
        'color_acento': '#818cf8',
        'color_texto': '#111827',
        'color_fondo': '#f5f7fb',
        'color_fondo_sidebar': '#312e81',
        'color_texto_sidebar': '#c7d2fe',
        'color_borde': '#e5e7eb',
        'color_peligro': '#dc2626',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
    {
        'nombre': 'Azul',
        'color_primario': '#2563eb',
        'color_secundario': '#3b82f6',
        'color_acento': '#60a5fa',
        'color_texto': '#111827',
        'color_fondo': '#f0f7ff',
        'color_fondo_sidebar': '#1e3a5f',
        'color_texto_sidebar': '#bfdbfe',
        'color_borde': '#dbeafe',
        'color_peligro': '#dc2626',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
    {
        'nombre': 'Verde',
        'color_primario': '#059669',
        'color_secundario': '#10b981',
        'color_acento': '#34d399',
        'color_texto': '#111827',
        'color_fondo': '#f0fdf4',
        'color_fondo_sidebar': '#064e3b',
        'color_texto_sidebar': '#a7f3d0',
        'color_borde': '#d1fae5',
        'color_peligro': '#dc2626',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
    {
        'nombre': 'Morado',
        'color_primario': '#7c3aed',
        'color_secundario': '#8b5cf6',
        'color_acento': '#a78bfa',
        'color_texto': '#111827',
        'color_fondo': '#f5f3ff',
        'color_fondo_sidebar': '#4c1d95',
        'color_texto_sidebar': '#ddd6fe',
        'color_borde': '#ede9fe',
        'color_peligro': '#dc2626',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
    {
        'nombre': 'Rojo',
        'color_primario': '#dc2626',
        'color_secundario': '#ef4444',
        'color_acento': '#f87171',
        'color_texto': '#111827',
        'color_fondo': '#fef2f2',
        'color_fondo_sidebar': '#7f1d1d',
        'color_texto_sidebar': '#fecaca',
        'color_borde': '#fee2e2',
        'color_peligro': '#b91c1c',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
    {
        'nombre': 'Naranja',
        'color_primario': '#ea580c',
        'color_secundario': '#f97316',
        'color_acento': '#fb923c',
        'color_texto': '#111827',
        'color_fondo': '#fff7ed',
        'color_fondo_sidebar': '#7c2d12',
        'color_texto_sidebar': '#fed7aa',
        'color_borde': '#ffedd5',
        'color_peligro': '#dc2626',
        'color_exito': '#16a34a',
        'color_advertencia': '#f59e0b',
    },
]
