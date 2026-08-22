from django.conf import settings
from django.db import models
from django.utils import timezone


class ConsentimientoInformado(models.Model):
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='consentimientos'
    )
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='consentimientos'
    )
    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.CASCADE,
        related_name='consentimientos'
    )

    tutor_nombre = models.CharField(max_length=200)
    tutor_cedula = models.CharField(max_length=20)
    tutor_parentesco = models.CharField(max_length=100)

    acepta_datos_personales = models.BooleanField(default=False)
    acepta_datos_academicos = models.BooleanField(default=False)
    acepta_datos_clinicos = models.BooleanField(default=False)
    acepta_comunicaciones = models.BooleanField(default=False)

    fecha_firma = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)
    motivo_revocacion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    ip_firma = models.GenericIPAddressField(null=True, blank=True)
    user_agent_firma = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_firma']
        verbose_name = 'Consentimiento Informado'
        verbose_name_plural = 'Consentimientos Informados'
        indexes = [
            models.Index(fields=['estudiante', 'activo'], name='consent_est_act'),
            models.Index(fields=['centro', 'anio_escolar'], name='consent_centro_anio'),
        ]

    def __str__(self):
        estado = 'Activo' if self.activo else 'Revocado'
        return f"{self.estudiante} - {self.tutor_nombre} ({estado})"

    def revocar(self, motivo=''):
        self.activo = False
        self.fecha_revocacion = timezone.now()
        self.motivo_revocacion = motivo
        self.save(update_fields=[
            'activo', 'fecha_revocacion', 'motivo_revocacion', 'updated_at'
        ])

    def tiene_consentimiento(self, tipo):
        if not self.activo:
            return False
        mapa = {
            'datos_personales': self.acepta_datos_personales,
            'datos_academicos': self.acepta_datos_academicos,
            'datos_clinicos': self.acepta_datos_clinicos,
            'comunicaciones': self.acepta_comunicaciones,
        }
        return mapa.get(tipo, False)


class RegistroAccesoDato(models.Model):
    TIPOS_DATO = [
        ('datos_personales', 'Datos Personales'),
        ('datos_academicos', 'Datos Académicos'),
        ('datos_clinicos', 'Datos Clínicos'),
        ('datos_tutor', 'Datos del Tutor'),
        ('historial_academico', 'Historial Académico'),
        ('constancia', 'Constancia/Certificado'),
        ('estadistico', 'Estadístico (anónimo)'),
    ]

    ACCIONES = [
        ('lectura', 'Lectura'),
        ('escritura', 'Escritura'),
        ('exportacion', 'Exportación'),
        ('eliminacion', 'Eliminación'),
        ('anonimizacion', 'Anonimización'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='accesos_datos'
    )
    tipo_dato = models.CharField(max_length=30, choices=TIPOS_DATO)
    accion = models.CharField(max_length=20, choices=ACCIONES)
    descripcion = models.TextField(blank=True)
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accesos_datos'
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Registro de Acceso a Dato'
        verbose_name_plural = 'Registros de Acceso a Datos'
        indexes = [
            models.Index(fields=['usuario', 'fecha'], name='acceso_user_fecha'),
            models.Index(fields=['tipo_dato', 'fecha'], name='acceso_tipo_fecha'),
            models.Index(fields=['estudiante', 'fecha'], name='acceso_est_fecha'),
        ]

    def __str__(self):
        return f"{self.usuario} → {self.get_tipo_dato_display()} ({self.get_accion_display()})"


class RegistroRetencion(models.Model):
    ACCIONES_RETENCION = [
        ('anonimizacion', 'Anonimización'),
        ('eliminacion', 'Eliminación'),
        ('exportacion_archivo', 'Exportación a archivo'),
    ]

    tipo_dato = models.CharField(max_length=30, choices=RegistroAccesoDato.TIPOS_DATO)
    accion = models.CharField(max_length=20, choices=ACCIONES_RETENCION)
    registros_afectados = models.PositiveIntegerField(default=0)
    detalle = models.JSONField(default=dict)
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    ejecutado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registros_retencion'
    )

    class Meta:
        ordering = ['-fecha_ejecucion']
        verbose_name = 'Registro de Retención'
        verbose_name_plural = 'Registros de Retención'

    def __str__(self):
        return f"{self.get_accion_display()} - {self.get_tipo_dato_display()} ({self.registros_afectados})"
