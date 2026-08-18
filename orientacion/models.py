from django.db import models

from core.models import AnioEscolar
from estudiantes.models import Estudiante
from usuarios.models import Usuario


class AlertaEstudiante(models.Model):
    """Alerta temprana: cruza cognitivo, académico, conductual, asistencia, salud y pago."""

    TIPOS = (
        ('cognitivo', 'Cognitivo'),
        ('academico', 'Académico'),
        ('conductual', 'Conductual'),
        ('asistencia', 'Asistencia'),
        ('salud', 'Salud'),
        ('pago', 'Pago'),
    )
    SEVERIDAD = (
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    )
    ESTADOS = (
        ('abierta', 'Abierta'),
        ('atendida', 'Atendida'),
        ('cerrada', 'Cerrada'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='alertas'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='alertas'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    severidad = models.CharField(max_length=20, choices=SEVERIDAD, default='media')
    descripcion = models.TextField()
    sugerencia = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierta')
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_creadas'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    atendida_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_atendidas'
    )
    atendida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estudiante', 'estado'], name='al_est_estado'),
            models.Index(fields=['tipo', 'estado'], name='al_tipo_estado'),
        ]

    def __str__(self):
        return f"Alerta {self.get_tipo_display()} - {self.estudiante}"


class PlanPedagogico(models.Model):
    """Adecuación curricular (acceso / no significativa / significativa)."""

    TIPOS = (
        ('acceso', 'Adecuación de acceso'),
        ('no_significativa', 'Adecuación no significativa'),
        ('significativa', 'Adecuación significativa'),
    )
    ORIGENES = (
        ('cognitivo', 'Perfil cognitivo'),
        ('conductual', 'Conducta'),
        ('salud', 'Salud'),
        ('academico', 'Rendimiento académico'),
        ('otro', 'Otro'),
    )
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('activo', 'Activo'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='planes_pedagogicos'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='planes_pedagogicos'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    origen = models.CharField(max_length=20, choices=ORIGENES, default='cognitivo')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    objetivos = models.TextField()
    estrategias = models.TextField(help_text='Estrategias y ajustes a implementar.')
    seguimiento = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planes_pedagogicos'
    )

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante}"


class IntervencionPsicopedagogica(models.Model):
    """Registro del orientador (timeline por estudiante)."""

    TIPOS = (
        ('sesion', 'Sesión de orientación'),
        ('observacion', 'Observación'),
        ('evaluacion', 'Evaluación psicopedagógica'),
        ('derivacion', 'Derivación'),
        ('seguimiento', 'Seguimiento'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='intervenciones'
    )
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    orientador = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intervenciones'
    )
    objetivo = models.CharField(max_length=255)
    estrategia = models.TextField(blank=True)
    resultado = models.TextField(blank=True)
    derivacion_a = models.CharField(
        max_length=150,
        blank=True,
        help_text='Especialista o servicio al que se deriva.'
    )

    class Meta:
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estudiante', 'fecha'], name='iv_est_fecha'),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante} ({self.fecha})"
