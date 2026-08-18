from django.db import models
from django.conf import settings
from academico.models import DocenteMateria, Grado
from core.models import AnioEscolar, CentroEducativo
from estudiantes.models import Estudiante

class Administrativo(models.Model):
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.CASCADE
    )

    # Datos personales
    foto = models.ImageField(
        'Foto',
        upload_to='administrativos/fotos/',
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
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    correo_personal = models.EmailField(blank=True, null=True)

    # Laboral
    CARGOS = (
        ('director', 'Director'),
        ('secretaria', 'Secretaria'),
        ('cajero', 'Cajero'),
    )
    cargo = models.CharField(max_length=20, choices=CARGOS)
    fecha_ingreso = models.DateField()
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
        return f"{self.nombre_completo()} - {self.get_cargo_display()}"

class Acta(models.Model):
    centro = models.ForeignKey(CentroEducativo, on_delete=models.CASCADE)
    anio_escolar = models.ForeignKey(AnioEscolar, on_delete=models.CASCADE)

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    seccion = models.CharField(max_length=5)

    fecha_generacion = models.DateTimeField(auto_now_add=True)

    datos = models.JSONField()  # 🔒 snapshot COMPLETO
    generado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = (
            'centro',
            'anio_escolar',
            'estudiante',
        )

    def __str__(self):
        return f"Acta {self.estudiante} - {self.anio_escolar}"
