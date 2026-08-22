from django.db import models
from django.utils import timezone


class Campania(models.Model):
    """Campaña de comunicación masiva o individual hacia los tutores.

    Se envía por correo electrónico, WhatsApp o ambos. El alcance puede ser
    todos los tutores del centro, los tutores de un grado (inscripción del año
    activo) o una selección concreta de tutores.
    """

    CANAL_CHOICES = [
        ('email', 'Correo electrónico'),
        ('whatsapp', 'WhatsApp'),
        ('ambos', 'Correo y WhatsApp'),
    ]

    ALCANCE_CHOICES = [
        ('todos', 'Todos los tutores'),
        ('grado', 'Tutores de un grado'),
        ('seleccion', 'Tutores seleccionados'),
    ]

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('parcial', 'Enviada con errores'),
        ('fallida', 'Fallida'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='campanias',
    )

    asunto = models.CharField(
        'Asunto',
        max_length=200,
        help_text='Asunto del correo. En WhatsApp se usa como encabezado.',
    )

    mensaje = models.TextField(
        'Mensaje',
        help_text=(
            'Contenido de la comunicación. Puedes usar {{tutor}} para el '
            'nombre del tutor y {{estudiante}} para el nombre del estudiante.'
        ),
    )

    canal = models.CharField(
        max_length=10,
        choices=CANAL_CHOICES,
        default='email',
    )

    alcance = models.CharField(
        max_length=20,
        choices=ALCANCE_CHOICES,
        default='todos',
    )

    grado = models.ForeignKey(
        'academico.Grado',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text='Solo se usan tutores de estudiantes inscritos en este grado durante el año activo.',
    )

    tutores = models.ManyToManyField(
        'tutores.Tutor',
        blank=True,
        related_name='campanias',
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
    )

    enviado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    enviado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Campaña'
        verbose_name_plural = 'Campañas'

    def __str__(self):
        return f"{self.asunto} · {self.get_canal_display()}"

    def resumen_estados(self):
        agrupado = {}
        for d in self.destinatarios.all():
            agrupado[d.estado] = agrupado.get(d.estado, 0) + 1
        return agrupado

    def total_destinatarios(self):
        return self.destinatarios.count()

    def total_exitosos(self):
        return self.destinatarios.filter(estado='enviado').count()

    @property
    def destinatarios_enviados(self):
        return self.destinatarios.filter(estado='enviado').count()

    @property
    def destinatarios_fallidos(self):
        return self.destinatarios.filter(estado='fallido').count()

    @property
    def destinatarios_sin_contacto(self):
        return self.destinatarios.filter(estado='sin_contacto').count()

    @property
    def destinatarios_pendientes(self):
        return self.destinatarios.filter(estado='pendiente').count()


class DestinatarioCampania(models.Model):
    """Un destinatario (tutor) por canal de una campaña."""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('sin_contacto', 'Sin contacto'),
    ]

    CANAL_CHOICES = Campania.CANAL_CHOICES

    campania = models.ForeignKey(
        Campania,
        on_delete=models.CASCADE,
        related_name='destinatarios',
    )
    tutor = models.ForeignKey(
        'tutores.Tutor',
        on_delete=models.CASCADE,
        related_name='campanias_recibidas',
    )
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    contacto = models.CharField(
        max_length=150,
        blank=True,
        help_text='Email o teléfono usado para el envío.',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )
    error = models.TextField(blank=True)
    enviado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('campania', 'tutor', 'canal')
        verbose_name = 'Destinatario de campaña'
        verbose_name_plural = 'Destinatarios de campaña'

    def __str__(self):
        return f"{self.tutor.nombre_completo()} · {self.canal}"


class NotificacionPago(models.Model):
    """Registro de las notificaciones automáticas de pago enviadas a tutores."""

    CANAL_CHOICES = Campania.CANAL_CHOICES

    ESTADO_CHOICES = [
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('sin_contacto', 'Sin contacto'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='notificaciones_pago',
    )
    pago = models.ForeignKey(
        'caja.Pago',
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    tutor = models.ForeignKey(
        'tutores.Tutor',
        on_delete=models.CASCADE,
        related_name='notificaciones_pago',
    )
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    contacto = models.CharField(max_length=150, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='enviado',
    )
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación de pago'
        verbose_name_plural = 'Notificaciones de pago'

    def __str__(self):
        return f"Pago {self.pago.recibo or self.pago_id} → {self.tutor.nombre_completo()} ({self.canal})"


class NotificacionPagoVencida(models.Model):
    """Registro de notificaciones automáticas por pagos vencidos."""

    CANAL_CHOICES = Campania.CANAL_CHOICES
    ESTADO_CHOICES = NotificacionPago.ESTADO_CHOICES

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='notificaciones_vencimiento',
    )
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='notificaciones_vencimiento',
    )
    tutor = models.ForeignKey(
        'tutores.Tutor',
        on_delete=models.CASCADE,
        related_name='notificaciones_vencimiento',
    )
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    contacto = models.CharField(max_length=150, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado')
    error = models.TextField(blank=True)
    monto_vencido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación de vencimiento'
        verbose_name_plural = 'Notificaciones de vencimiento'
        unique_together = ('centro', 'estudiante', 'tutor', 'fecha')

    def __str__(self):
        return f"Vencimiento {self.estudiante} → {self.tutor} ({self.canal})"


class Comunicado(models.Model):
    """Anuncio/comunicado visible en los portales de estudiante y tutor.

    El alcance puede ser todo el centro o una seccion concreta: en ese caso
    solo lo ven los estudiantes inscritos en esa seccion durante el ano
    escolar activo (y los tutores de esos estudiantes).
    """

    ALCANCE_CHOICES = [
        ('todos', 'Todo el centro'),
        ('seccion', 'Una seccion'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='comunicados',
    )

    titulo = models.CharField('Titulo', max_length=200)

    contenido = models.TextField(
        'Contenido',
        help_text='Texto del comunicado que veran estudiantes y tutores.',
    )

    alcance = models.CharField(
        max_length=10,
        choices=ALCANCE_CHOICES,
        default='todos',
    )

    seccion = models.ForeignKey(
        'academico.Seccion',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='comunicados',
        help_text='Solo se usa cuando el alcance es una seccion.',
    )

    fecha_publicacion = models.DateTimeField(
        'Fecha de publicacion',
        default=timezone.now,
    )

    fecha_vencimiento = models.DateField(
        'Vence el',
        null=True,
        blank=True,
        help_text='Opcional: despues de esta fecha deja de mostrarse.',
    )

    fijado = models.BooleanField(
        'Fijado arriba',
        default=False,
        help_text='Los comunicados fijados aparecen primero.',
    )

    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comunicados_publicados',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fijado', '-fecha_publicacion']
        verbose_name = 'Comunicado'
        verbose_name_plural = 'Comunicados'

    def __str__(self):
        destino = self.seccion.nombre if self.seccion_id else 'Todo el centro'
        return f"{self.titulo} ({destino})"

    def esta_vigente(self, fecha=None):
        """True si ya publico y no ha vencido (comparando fechas locales)."""
        fecha = fecha or timezone.localdate()

        if self.fecha_publicacion:
            publicada = self.fecha_publicacion
            if timezone.is_aware(publicada):
                publicada = timezone.localtime(publicada).date()
            else:
                publicada = publicada.date()
            if publicada > fecha:
                return False

        if self.fecha_vencimiento and self.fecha_vencimiento < fecha:
            return False
        return True

    @property
    def vencido(self):
        return not self.esta_vigente()
