from django.db import models

from core.models import CentroEducativo, AnioEscolar
from usuarios.models import Usuario


class DiaNoDocencia(models.Model):
    """Día dentro del año escolar en el que NO se imparte docencia
    (feriados, asuetos, etc.). Estos días no cuentan en el promedio
    de asistencia de los estudiantes."""

    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.CASCADE,
        related_name='dias_no_docencia'
    )

    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='dias_no_docencia'
    )

    fecha = models.DateField()

    motivo = models.CharField(
        max_length=255,
        help_text='Ej: Feriado nacional, día de asueto, actividad institucional.'
    )

    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('centro', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha} - {self.motivo}"


class AsistenciaEstudiante(models.Model):

    ESTADOS = (
        ('presente', 'Presente'),
        ('tardanza', 'Tardanza'),
        ('justificado', 'Justificado'),
        ('ausente', 'Ausente'),
    )

    # Estados que cuentan como día asistido
    ESTADOS_ASISTIDO = ('presente', 'tardanza', 'justificado')

    inscripcion = models.ForeignKey(
        'estudiantes.Inscripcion',
        on_delete=models.CASCADE,
        related_name='asistencias'
    )

    fecha = models.DateField()

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS
    )

    registrada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_registradas'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('inscripcion', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.inscripcion.estudiante} - {self.fecha} - {self.get_estado_display()}"
