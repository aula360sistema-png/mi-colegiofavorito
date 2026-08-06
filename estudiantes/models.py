from datetime import date

from django.db import models


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        Estudiante,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=150)

    archivo = models.FileField(
        upload_to='estudiantes/documentos/'
    )

    fecha_subida = models.DateTimeField(
        auto_now_add=True
    )

class Inscripcion(models.Model):
    ESTADO_FINALES = [
        ('pendiente', 'Pendiente'), 
        ('aprobado', 'Aprobado'), 
        ('reprobado', 'Reprobado'), 
        ('retirado', 'Retirado'),
        ('sin_calificacion', 'Sin Calificación'),
    ]


    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE
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