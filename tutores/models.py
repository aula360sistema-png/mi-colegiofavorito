from django.db import models


class Tutor(models.Model):
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
        upload_to='tutores/fotos/',
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

    # Contacto
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20)
    telefono_secundario = models.CharField(max_length=20, blank=True, null=True)
    correo_personal = models.EmailField(blank=True, null=True)

    PARENTESCOS = (
        ('padre', 'Padre'),
        ('madre', 'Madre'),
        ('tutor_legal', 'Tutor legal'),
        ('abuelo', 'Abuelo(a)'),
        ('tio', 'Tío(a)'),
        ('hermano', 'Hermano(a)'),
        ('otro', 'Otro'),
    )
    parentesco = models.CharField(
        max_length=20,
        choices=PARENTESCOS,
        default='tutor_legal'
    )

    # Estudiantes a cargo
    estudiantes = models.ManyToManyField(
        'estudiantes.Estudiante',
        related_name='tutores',
        blank=True
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

    class Meta:
        ordering = ['primer_apellido', 'primer_nombre']
