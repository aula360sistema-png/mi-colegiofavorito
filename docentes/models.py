from django.db import models


class Docente(models.Model):
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    centro = models.ForeignKey(
        'core.CentroEducativo',
        on_delete=models.CASCADE
    )

    # Datos personales
    foto = models.ImageField(
        'Foto',
        upload_to='docentes/fotos/',
        blank=True,
        null=True
    )

    primer_nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)

    cedula = models.CharField(max_length=13, unique=True)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    fecha_nacimiento = models.DateField()
    nacionalidad = models.CharField(max_length=100)

    # Dirección
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    correo_personal = models.EmailField(blank=True, null=True)

    # Datos laborales
    codigo_docente_minerd = models.CharField(max_length=50, unique=True)
    area_especialidad = models.CharField(max_length=150)
    fecha_ingreso = models.DateField()

    tipo_contrato = models.CharField(
        max_length=20,
        choices=[('nombrado', 'Nombrado'), ('contratado', 'Contratado')]
    )

    tanda = models.CharField(
        max_length=20,
        choices=[('matutina', 'Matutina'), ('vespertina', 'Vespertina'), ('nocturna', 'Nocturna')]
    )

    estado = models.CharField(
        max_length=20,
        choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')],
        default='activo'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def nombre_completo(self):
        return f"{self.primer_nombre} {self.segundo_nombre or ''} {self.primer_apellido} {self.segundo_apellido or ''}".strip()

    def __str__(self):
        return self.nombre_completo()


class AsignacionDocente(models.Model):
    docente = models.ForeignKey(
        Docente,
        on_delete=models.CASCADE
    )
 
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)

    anio_escolar = models.ForeignKey(
        'core.AnioEscolar',
        on_delete=models.CASCADE
    )

    area = models.ForeignKey(
        'academico.AreaCurricular',
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

    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            'docente',
            'centro',
            'anio_escolar',
            'area',
            'grado',
            'seccion'
        )

