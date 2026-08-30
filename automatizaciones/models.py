from django.db import models
from django.utils import timezone


class NotificacionAutomatica(models.Model):
    """Registro de las alertas generadas desde el tablero de automatizaciones.

    Cada registro apunta a la campaña en borrador creada para avisar a los
    tutores de los estudiantes afectados. El envío final lo revisa el
    personal desde comunicaciones.
    """

    TIPO_CHOICES = [
        ('inasistencias', 'Inasistencias consecutivas'),
        ('notas_rojas', 'Notas en rojo'),
        ('pagos_vencidos', 'Pagos vencidos'),
        ('cumpleanos', 'Cumpleaños'),
    ]

    CANAL_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('ambos', 'Correo y WhatsApp'),
    ]

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='notificaciones_automaticas',
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    campania = models.ForeignKey(
        'comunicaciones.Campania',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='automatizaciones',
    )
    canal = models.CharField(
        max_length=10,
        choices=CANAL_CHOICES,
        default='email',
    )
    total_destinatarios = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación automática'
        verbose_name_plural = 'Notificaciones automáticas'

    def __str__(self):
        return f'{self.titulo} ({self.total_destinatarios})'