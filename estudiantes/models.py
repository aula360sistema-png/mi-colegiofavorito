import os
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from seguridad.fields import EncryptedCharField, EncryptedTextField


class Estudiante(models.Model):
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.CASCADE
    )

    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )

    # Datos personales
    matricula = models.CharField(max_length=50, unique=True)

    foto = models.ImageField(
        'Foto',
        upload_to='estudiantes/fotos/',
        blank=True,
        null=True
    )

    primer_nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)

    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(max_length=150)
    nacionalidad = models.CharField(max_length=100)

    # Dirección
    direccion = models.TextField()
    telefono = models.CharField(max_length=20, blank=True, null=True)

    # Tutor
    nombre_tutor = models.CharField(max_length=200)
    cedula_tutor = models.CharField(max_length=13)
    telefono_tutor = models.CharField(max_length=20)
    parentesco_tutor = models.CharField(max_length=50)

  

    estado = models.CharField(
        max_length=20,
        choices=[('activo', 'Activo'), ('retirado', 'Retirado'), ('egresado', 'Egresado')],
        default='activo'
    )

    MODALIDADES_SALIDA = (
        ('general', 'Modalidad General'),
        ('ciencias_letras', 'Ciencias y Letras'),
        ('ciencias_fisicas_matematicas', 'Ciencias Físicas y Matemáticas'),
        ('ciencias_fisicas_naturales', 'Ciencias Físicas y Naturales'),
        ('filosofia_letras', 'Filosofía y Letras'),
    )

    modalidad_salida = models.CharField(
        max_length=50,
        choices=MODALIDADES_SALIDA,
        blank=True,
        null=True,
        verbose_name='Modalidad de salida',
        help_text='Modalidad de salida del bachiller (solo Nivel Secundario).'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['centro'], name='est_centro'),
            models.Index(fields=['centro', 'estado'], name='est_centro_estado'),
        ]

    def nombre_completo(self):
        return f"{self.primer_nombre} {self.segundo_nombre or ''} {self.primer_apellido} {self.segundo_apellido or ''}".strip()

    from datetime import date

 

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None

        hoy = date.today()

        return (
            hoy.year
            - self.fecha_nacimiento.year
            - (
                (hoy.month, hoy.day)
                <
                (
                    self.fecha_nacimiento.month,
                    self.fecha_nacimiento.day
                )
            )
        )

    def __str__(self):
        return self.nombre_completo()

class DocumentoEstudiante(models.Model):
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='documentos'
    )

    nombre = models.CharField(max_length=150)

    archivo = models.FileField(
        upload_to='estudiantes/documentos/'
    )

    fecha_subida = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        super().clean()
        nombre = self.archivo.name if self.archivo else ''
        extension = os.path.splitext(nombre)[1].lower()
        permitidas = getattr(settings, 'ALLOWED_DOCUMENT_EXTENSIONS', {'.pdf', '.jpg', '.jpeg', '.png'})
        if nombre and extension not in permitidas:
            raise ValidationError({
                'archivo': f'Tipo de archivo no permitido ({extension}). '
                           f'Extensiones aceptadas: {", ".join(sorted(permitidas))}.',
            })
        if self.archivo and self.archivo.size > 5 * 1024 * 1024:
            raise ValidationError({'archivo': 'El archivo no puede superar los 5 MB.'})

class ObservacionEstudiante(models.Model):
    TIPOS = (
        ('observacion', 'Observación'),
        ('conducta', 'Conducta'),
        ('merito', 'Mérito / Reconocimiento'),
        ('amonestacion', 'Amonestación'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='observaciones'
    )

    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='observaciones_estudiantes'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='observacion'
    )

    fecha = models.DateField(default=date.today)

    descripcion = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha']

        indexes = [
            models.Index(fields=['estudiante'], name='obs_estudiante'),
            models.Index(fields=['anio_escolar'], name='obs_anio'),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante} - {self.fecha}"


class Inscripcion(models.Model):
    ESTADO_FINALES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('reprobado', 'Reprobado'),
        ('recuperacion', 'Recuperación'),
        ('retirado', 'Retirado'),
        ('sin_calificacion', 'Sin Calificación'),
    ]


    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='inscripciones'
    )
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )
    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.PROTECT
    )
    grado = models.ForeignKey(
        'academico.Grado',
        on_delete=models.PROTECT
    )
    seccion = models.ForeignKey(
        'academico.Seccion',
        on_delete=models.PROTECT
    )
    fecha = models.DateField(auto_now_add=True)

    promedio_final = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    estado_final = models.CharField(max_length=20, choices=ESTADO_FINALES, default='pendiente')
    fecha_cierre = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.estudiante.nombre_completo()} - {self.centro.nombre} - {self.anio_escolar.nombre} - {self.grado.nombre} - {self.seccion.nombre}"

    class Meta:
        unique_together = ('estudiante', 'anio_escolar')

        indexes = [
            models.Index(fields=['centro', 'anio_escolar'], name='insc_centro_anio'),
            models.Index(fields=['estudiante'], name='insc_estudiante'),
            models.Index(fields=['estado_final'], name='insc_estado_final'),
        ]


class HistorialAcademico(models.Model):
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE
    )

    nivel = models.ForeignKey(
        'academico.Nivel',
        on_delete=models.PROTECT
    )

    grado = models.ForeignKey(
        'academico.Grado',
        on_delete=models.PROTECT
    )

    seccion = models.ForeignKey(
        'academico.Seccion',
        on_delete=models.PROTECT
    )

    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.PROTECT
    )

    estado = models.CharField(
    max_length=20,
    choices=Inscripcion.ESTADO_FINALES,
    default='aprobado'
)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    cerrado = models.BooleanField(default=False)


class SolicitudCertificado(models.Model):
    TIPOS_CERTIFICADO = [
        ('constancia_estudio', 'Constancia de Estudios'),
        ('record_notas', 'Récord de Notas'),
        ('constancia_conducta', 'Constancia de Conducta'),
    ]

    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('pagada', 'Pagada'),
        ('entregada', 'Entregada'),
        ('anulada', 'Anulada'),
    ]

    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('online', 'En línea'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False)

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='solicitudes_certificados'
    )

    solicitante = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_certificados'
    )

    tipo_certificado = models.CharField(
        max_length=30,
        choices=TIPOS_CERTIFICADO,
        default='constancia_estudio'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='pendiente'
    )

    motivo = models.TextField(blank=True)

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        default='efectivo'
    )

    referencia_pago = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referencia de la pasarela o del comprobante de pago."
    )

    pagado = models.BooleanField(default=False)
    pagado_en = models.DateTimeField(null=True, blank=True)

    aprobado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificados_aprobados'
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)

    entregado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificados_entregados'
    )
    entregado_en = models.DateTimeField(null=True, blank=True)

    rechazo_motivo = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.folio:
            anio = (self.created_at or date.today()).year
            ultimo = (
                SolicitudCertificado.objects
                .filter(folio__startswith=f"SC-{anio}-")
                .order_by('-folio')
                .first()
            )
            if ultimo:
                numero = int(ultimo.folio.rsplit('-', 1)[1]) + 1
            else:
                numero = 1
            self.folio = f"SC-{anio}-{numero:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} - {self.estudiante} - {self.get_estado_display()}"


class HistorialClinicoEstudiante(models.Model):
    GRUPOS_SANGUINEOS = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('desconocido', 'No especificado'),
    ]

    estudiante = models.OneToOneField(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='historial_clinico'
    )

    grupo_sanguineo = models.CharField(
        max_length=20,
        choices=GRUPOS_SANGUINEOS,
        default='desconocido'
    )

    alergias = EncryptedTextField(
        blank=True,
        help_text="Alergias a medicamentos, alimentos u otros."
    )

    condiciones_medicas = EncryptedTextField(
        blank=True,
        help_text="Enfermedades crónicas, condiciones o diagnósticos relevantes."
    )

    medicamentos_habituales = EncryptedTextField(
        blank=True,
        help_text="Medicamentos que toma de forma habitual."
    )

    vacunas = EncryptedTextField(
        blank=True,
        help_text="Vacunas y dosis (opcional)."
    )

    contacto_emergencia_nombre = EncryptedCharField(
        max_length=512,
        blank=True
    )

    contacto_emergencia_telefono = EncryptedCharField(
        max_length=512,
        blank=True
    )

    contacto_emergencia_parentesco = EncryptedCharField(
        max_length=512,
        blank=True
    )

    contacto_emergencia_secundario_nombre = EncryptedCharField(
        max_length=512,
        blank=True
    )

    contacto_emergencia_secundario_telefono = EncryptedCharField(
        max_length=512,
        blank=True
    )

    observaciones = EncryptedTextField(
        blank=True,
        help_text="Cualquier otra información relevante para emergencias."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Historial clínico - {self.estudiante.nombre_completo()}"


class RegistroSalud(models.Model):
    TIPOS = [
        ('enfermedad', 'Enfermedad'),
        ('accidente', 'Accidente'),
        ('emergencia', 'Emergencia'),
        ('atencion', 'Atención general'),
        ('vacuna', 'Vacuna'),
    ]

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='registros_salud'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='atencion'
    )

    fecha = models.DateField()

    descripcion = models.TextField()

    atencion_proporcionada = models.TextField(
        blank=True,
        help_text="Qué se hizo o qué atención se prestó."
    )

    medicamento = models.CharField(
        max_length=200,
        blank=True,
        help_text="Medicamento administrado o indicado."
    )

    notificado_a_tutor = models.BooleanField(
        default=False,
        help_text="¿Se notificó al tutor/representante?"
    )

    registrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_salud'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-created_at']

        indexes = [
            models.Index(fields=['estudiante'], name='rsalud_estudiante'),
        ]

    def __str__(self):
        return (
            f"{self.estudiante.nombre_completo()} - "
            f"{self.get_tipo_display()} - {self.fecha}"
        )
