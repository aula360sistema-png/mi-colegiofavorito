from django.db import models

from core.models import AnioEscolar
from estudiantes.models import Estudiante


class TramoEdad(models.Model):
    """Tramo de edad que define qué destrezas se entrenan (catálogo global)."""

    nombre = models.CharField(max_length=60)
    edad_min = models.PositiveIntegerField()
    edad_max = models.PositiveIntegerField()
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['edad_min', 'edad_max', 'nombre']
        unique_together = ('edad_min', 'edad_max')

    def __str__(self):
        return self.nombre


class DestrezaCognitiva(models.Model):
    CATEGORIAS = (
        ('atencion', 'Atención'),
        ('memoria', 'Memoria de trabajo'),
        ('lectura', 'Fluidez lectora'),
        ('comprension', 'Comprensión'),
        ('logica', 'Pensamiento lógico-matemático'),
        ('metacognicion', 'Metacognición y pensamiento crítico'),
    )

    tramo = models.ForeignKey(
        TramoEdad,
        on_delete=models.CASCADE,
        related_name='destrezas'
    )
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['tramo', 'orden', 'nombre']
        unique_together = ('tramo', 'nombre')
        indexes = [
            models.Index(fields=['categoria'], name='dc_categoria'),
        ]

    def __str__(self):
        return f"{self.tramo} - {self.nombre}"


class UnidadEntrenamiento(models.Model):
    """Secuencia de unidades dentro de un tramo (análogo a los circuitos de Progrentis)."""

    tramo = models.ForeignKey(
        TramoEdad,
        on_delete=models.CASCADE,
        related_name='unidades'
    )
    numero = models.PositiveIntegerField()
    nombre = models.CharField(max_length=150)
    destrezas = models.ManyToManyField(
        DestrezaCognitiva,
        related_name='unidades',
        blank=True
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['tramo', 'numero']
        unique_together = ('tramo', 'numero')

    def __str__(self):
        return f"{self.tramo} - U{self.numero}: {self.nombre}"


class Ejercicio(models.Model):
    """Ítem del banco de ejercicios (contenido, no resultado de un alumno)."""

    TIPOS = (
        ('seleccion', 'Selección'),
        ('verdadero_falso', 'Verdadero / Falso'),
        ('completar', 'Completar'),
        ('secuencia', 'Secuencia / orden'),
        ('filtrado', 'Filtrado'),
        ('comprension', 'Comprensión de lectura'),
        ('calculo', 'Cálculo mental'),
    )

    DIFICULTADES = (
        (1, 'Fácil'),
        (2, 'Media'),
        (3, 'Difícil'),
        (4, 'Muy difícil'),
        (5, 'Experto'),
    )

    unidad = models.ForeignKey(
        UnidadEntrenamiento,
        on_delete=models.CASCADE,
        related_name='ejercicios'
    )
    destreza = models.ForeignKey(
        DestrezaCognitiva,
        on_delete=models.CASCADE,
        related_name='ejercicios'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    dificultad = models.PositiveIntegerField(default=1, choices=DIFICULTADES)
    enunciado = models.TextField()
    texto = models.TextField(
        blank=True,
        help_text='Pasaje de lectura, opcional según el tipo.'
    )
    opciones = models.JSONField(
        default=list,
        blank=True,
        help_text='Opciones: [{"texto": "...", "correcta": false}]'
    )
    respuesta_correcta = models.TextField(
        blank=True,
        help_text='Respuesta cuando el tipo no usa opciones.'
    )
    tiempo_max_seg = models.PositiveIntegerField(default=60)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['unidad', 'destreza', 'dificultad']
        indexes = [
            models.Index(fields=['destreza', 'activo'], name='ej_destreza_activo'),
        ]

    def __str__(self):
        return f"{self.unidad} - {self.destreza} ({self.get_tipo_display()})"


class DiagnosticoCognitivo(models.Model):
    """Prueba inicial del alumno al entrar a un tramo (baseline del perfil)."""

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='diagnosticos_cognitivos'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='diagnosticos_cognitivos'
    )
    tramo = models.ForeignKey(TramoEdad, on_delete=models.PROTECT)
    fecha = models.DateField(auto_now_add=True)
    resultado = models.JSONField(
        default=dict,
        help_text='Por destreza: {destreza_id: {"aciertos": n, "errores": n, '
                  '"nivel": "bajo"|"medio"|"alto"}}'
    )
    ipd = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Índice de Productividad Digital inicial (0-100).'
    )

    class Meta:
        unique_together = ('estudiante', 'anio_escolar')
        indexes = [
            models.Index(fields=['estudiante', 'anio_escolar'], name='diag_est_anio'),
        ]

    def __str__(self):
        return f"Diagnóstico {self.estudiante} - {self.anio_escolar}"


class SesionEntrenamiento(models.Model):
    ESTADOS = (
        ('en_progreso', 'En progreso'),
        ('completada', 'Completada'),
        ('abandonada', 'Abandonada'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='sesiones_entrenamiento'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='sesiones_entrenamiento'
    )
    unidad = models.ForeignKey(
        UnidadEntrenamiento,
        on_delete=models.PROTECT,
        related_name='sesiones'
    )
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_seg = models.PositiveIntegerField(default=0)
    items_total = models.PositiveIntegerField(default=0)
    aciertos = models.PositiveIntegerField(default=0)
    errores = models.PositiveIntegerField(default=0)
    ipd = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Índice de Productividad Digital de la sesión (0-100).'
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='en_progreso')

    class Meta:
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['estudiante', 'fecha_inicio'], name='se_est_fecha'),
            models.Index(fields=['estudiante', 'anio_escolar'], name='se_est_anio'),
        ]

    def __str__(self):
        return f"Sesión {self.estudiante} - {self.unidad} ({self.estado})"


class IntentoEjercicio(models.Model):
    sesion = models.ForeignKey(
        SesionEntrenamiento,
        on_delete=models.CASCADE,
        related_name='intentos'
    )
    ejercicio = models.ForeignKey(
        Ejercicio,
        on_delete=models.CASCADE,
        related_name='intentos'
    )
    acierto = models.BooleanField(default=False)
    tiempo_respuesta_ms = models.PositiveIntegerField(default=0)
    dificultad_aplicada = models.PositiveIntegerField(default=1)
    respuesta_dada = models.TextField(blank=True)

    class Meta:
        unique_together = ('sesion', 'ejercicio')
        indexes = [
            models.Index(fields=['ejercicio'], name='int_ejercicio'),
        ]

    def __str__(self):
        return f"{self.sesion} - {self.ejercicio} ({'OK' if self.acierto else 'X'})"


class MetricaCognitiva(models.Model):
    """Snapshot IPD/percentil al cierre de periodo (récord histórico)."""

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='metricas_cognitivas'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='metricas_cognitivas'
    )
    periodo = models.ForeignKey(
        'academico.PeriodoAnio',
        on_delete=models.CASCADE,
        related_name='metricas_cognitivas'
    )
    tramo = models.ForeignKey(TramoEdad, on_delete=models.PROTECT)
    fecha_corte = models.DateField()
    ipd = models.DecimalField(max_digits=6, decimal_places=2)
    percentil_edad = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Percentil respecto a la distribución del mismo tramo en el '
                  'centro (0-100).'
    )
    desglose = models.JSONField(
        default=dict,
        help_text='Por destreza: {destreza_id: {"aciertos": n, "errores": n, '
                  '"tiempo_promedio_ms": n, "nivel": "...", "percentil": n}}'
    )

    class Meta:
        unique_together = ('estudiante', 'anio_escolar', 'periodo')
        ordering = ['-fecha_corte']

    def __str__(self):
        return f"{self.estudiante} {self.periodo.periodo} - IPD {self.ipd}"


class PlanRefuerzo(models.Model):
    GENERADO_POR = (
        ('auto', 'Automático'),
        ('docente', 'Docente'),
        ('orientador', 'Orientador'),
        ('ia', 'IA'),
    )
    ORIGENES = (
        ('destrezas_bajas', 'Destrezas bajas'),
        ('alerta', 'Alerta'),
        ('adecuacion', 'Adecuación curricular'),
        ('manual', 'Manual'),
    )
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('activo', 'Activo'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='planes_refuerzo'
    )
    anio_escolar = models.ForeignKey(
        AnioEscolar,
        on_delete=models.CASCADE,
        related_name='planes_refuerzo'
    )
    unidad = models.ForeignKey(
        UnidadEntrenamiento,
        on_delete=models.PROTECT,
        related_name='planes_refuerzo',
        null=True,
        blank=True
    )
    fecha_generado = models.DateField(auto_now_add=True)
    generado_por = models.CharField(max_length=20, choices=GENERADO_POR, default='auto')
    origen = models.CharField(max_length=20, choices=ORIGENES, default='destrezas_bajas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    nota = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_generado']

    def __str__(self):
        return f"Refuerzo {self.estudiante} ({self.estado})"


class ItemPlanRefuerzo(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('superado', 'Superado'),
    )

    plan = models.ForeignKey(
        PlanRefuerzo,
        on_delete=models.CASCADE,
        related_name='items'
    )
    destreza = models.ForeignKey(
        DestrezaCognitiva,
        on_delete=models.CASCADE,
        related_name='items_refuerzo'
    )
    ejercicio = models.ForeignKey(
        Ejercicio,
        on_delete=models.CASCADE,
        related_name='items_refuerzo'
    )
    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    class Meta:
        ordering = ['plan', 'orden']
        unique_together = ('plan', 'ejercicio')

    def __str__(self):
        return f"{self.plan} - {self.ejercicio}"
