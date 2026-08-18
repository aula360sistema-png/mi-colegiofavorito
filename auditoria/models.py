from django.db import models
from django.conf import settings


class Bitacora(models.Model):

    ACCIONES = (
        ('CREAR', 'CREAR'),
        ('EDITAR', 'EDITAR'),
        ('ELIMINAR', 'ELIMINAR'),
        ('LOGIN', 'LOGIN'),
        ('LOGOUT', 'LOGOUT'),
        ('LOGIN_FAILED', 'LOGIN_FAILED'),
        ('DESCARGA', 'DESCARGA'),
('PASSWORD_CHANGE', 'PASSWORD_CHANGE'),
('ACCESO_DENEGADO', 'ACCESO_DENEGADO'),
('EXPORTAR', 'EXPORTAR'),
('IMPORTAR', 'IMPORTAR'),
('ACTIVAR_2FA', 'ACTIVAR_2FA'),
('DESACTIVAR_2FA', 'DESACTIVAR_2FA'),
    )

    NIVELES_RIESGO = (
        ('BAJO', 'BAJO'),
        ('MEDIO', 'MEDIO'),
        ('ALTO', 'ALTO'),
        ('CRITICO', 'CRITICO'),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    accion = models.CharField(
        max_length=30,
        choices=ACCIONES
    )

    modulo = models.CharField(max_length=100)

    descripcion = models.TextField()

    modelo = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    objeto_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    ruta = models.TextField(
        null=True,
        blank=True
    )

    metodo = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    navegador = models.TextField(
        null=True,
        blank=True
    )

    tipo_dispositivo = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    riesgo = models.CharField(
        max_length=20,
        choices=NIVELES_RIESGO,
        default='BAJO'
    )

    datos_anteriores = models.JSONField(
        null=True,
        blank=True
    )

    datos_nuevos = models.JSONField(
        null=True,
        blank=True
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Bitácora'
        verbose_name_plural = 'Bitácoras'
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['usuario', 'fecha']),
        ]

    def __str__(self):
        return f"{self.accion} - {self.modulo}"