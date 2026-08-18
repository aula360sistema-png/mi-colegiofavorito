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
