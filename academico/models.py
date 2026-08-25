from django.db import models
class Nivel(models.Model):
    TIPOS = (
        ('inicial', 'Nivel Inicial'),
        ('primaria', 'Nivel Primario'),
        ('secundaria', 'Nivel Secundario'),
    )

    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    tipo = models.CharField(
        "Tipo de plantilla",
        max_length=20,
        choices=TIPOS,
        default='primaria'
    )

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('centro', 'tipo')


class Grado(models.Model):
    nivel = models.ForeignKey(Nivel, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField(default=0)
    ciclo = models.PositiveIntegerField(
        default=1,
        help_text='Ciclo del nivel según el currículo MINERD (1 o 2).'
    )
    secciones = models.ManyToManyField(
        'Seccion',
        blank=True,
        related_name='grados',
        help_text='Secciones que usa este grado (ej: A, B, C).'
    )
    def __str__(self):
            return self.nombre

    class Meta:
        ordering = ['nivel', 'orden', 'nombre']
        unique_together = ('nivel', 'nombre')


class Seccion(models.Model):
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=5)

    class Meta:
        ordering = ['nombre']
        unique_together = ('centro', 'nombre')

    def __str__(self):
        return self.nombre


class AreaCurricular(models.Model):
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    def __str__(self):
            return self.nombre


class Asignatura(models.Model):
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    area = models.ForeignKey(AreaCurricular, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=150)
    def __str__(self):
        return self.nombre


class GradoAsignatura(models.Model):
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('grado', 'asignatura')
    
    def __str__ (self):
        return f"{self.grado}-{self.asignatura}"


class Competencia(models.Model):
    nivel = models.ForeignKey(
        Nivel,
        on_delete=models.CASCADE,
        related_name='competencias',
        verbose_name='Nivel',
    )
    nombre = models.CharField(max_length=150)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nivel', 'orden', 'nombre']
        unique_together = ('nivel', 'nombre')

    def __str__(self):
        return self.nombre

class AreaCompetencia(models.Model):
    area = models.ForeignKey(AreaCurricular, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    peso = models.DecimalField(max_digits=5, decimal_places=2)

class Periodo(models.Model):
    # Catálogo reutilizable por centro (sin anio_escolar).
    # El estado por año escolar vive en PeriodoAnio.
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=20)  # P1, P2...
    orden = models.PositiveIntegerField()
    es_completivo = models.BooleanField(default=False)

    class Meta:
        ordering = ['orden', 'nombre']
        unique_together = ('centro', 'nombre')

    def __str__(self):
        return self.nombre


class PeriodoAnio(models.Model):
    # Estado de un período del catálogo para un año escolar concreto.
    periodo = models.ForeignKey(
        Periodo,
        on_delete=models.CASCADE,
        related_name='estados'
    )
    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.CASCADE,
        related_name='periodos_estado'
    )
    activo = models.BooleanField(default=True)
    cerrado = models.BooleanField(default=False)
    fecha_cierre = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['periodo__orden', 'periodo__nombre']
        unique_together = ('periodo', 'anio_escolar')

        indexes = [
            models.Index(fields=['anio_escolar'], name='pa_anio'),
        ]

    def __str__(self):
        return f"{self.periodo} - {self.anio_escolar}"


class DocenteMateria(models.Model):
    docente = models.ForeignKey('docentes.Docente', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)

    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)

    anio_escolar = models.ForeignKey('core.AnioEscolar', on_delete=models.CASCADE)

    def __str__(self):
        return (
            f"{self.docente} | "
            f"{self.asignatura} | "
            f"{self.grado}-{self.seccion} | "
            f"{self.anio_escolar}"
        )

         

    class Meta:
        unique_together = (

            'asignatura',
            'grado',
            'seccion',
            'anio_escolar'
        )

        indexes = [
            models.Index(
                fields=['grado', 'seccion', 'anio_escolar'],
                name='dm_grado_seccion_anio',
            ),
            models.Index(fields=['docente', 'anio_escolar'], name='dm_docente_anio'),
        ]
    



class Calificacion(models.Model):
    ORIGEN_CHOICES = (
        ('docente', 'Docente'),
        ('sistema', 'Sistema (cierre forzado)'),
    )

    inscripcion = models.ForeignKey(
        'estudiantes.Inscripcion',
        on_delete=models.CASCADE
    )

    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT)

    nota = models.DecimalField(max_digits=5, decimal_places=2)

    # Trazabilidad: 'docente' = la cargó el docente; 'sistema' = cero
    # automático generado al forzar el cierre de un período.
    origen = models.CharField(
        'Origen de la nota',
        max_length=10,
        choices=ORIGEN_CHOICES,
        default='docente',
        help_text=(
            "Quién registró la nota. Las notas 'Sistema' fueron puestas "
            "en 0 automáticamente al forzar un cierre de período."
        ),
    )

    class Meta:
        unique_together = (
            'inscripcion',
            'asignatura',
            'competencia',
            'periodo'
        )

        indexes = [
            models.Index(fields=['inscripcion'], name='cal_inscripcion'),
            models.Index(fields=['periodo'], name='cal_periodo'),
            models.Index(fields=['asignatura'], name='cal_asignatura'),
        ]


class FranjaHoraria(models.Model):
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE,
        related_name='franjas_horarias'
    )
    nombre = models.CharField(max_length=80, help_text='Ej: 1ra hora, Recreo, 3ra hora')
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden', 'hora_inicio']
        unique_together = ('centro', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio:%H:%M} - {self.hora_fin:%H:%M})"


class HorarioClase(models.Model):
    DIAS_SEMANA = (
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
    )

    asignacion = models.ForeignKey(
        DocenteMateria,
        on_delete=models.CASCADE,
        related_name='horarios'
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS_SEMANA)
    franja = models.ForeignKey(
        FranjaHoraria,
        on_delete=models.CASCADE,
        related_name='clases'
    )

    class Meta:
        ordering = ['dia_semana', 'franja__orden']
        unique_together = ('asignacion', 'dia_semana', 'franja')

    def __str__(self):
        return (
            f"{self.get_dia_semana_display()} {self.franja.nombre} | "
            f"{self.asignacion}"
        )
