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


class Grado(models.Model):
    nivel = models.ForeignKey(Nivel, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField(default=0)
    def __str__(self):
            return self.nombre

    class Meta:
        ordering = ['nivel', 'orden', 'nombre']


class Seccion(models.Model):
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=5)
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
    nombre = models.CharField(max_length=150)
    def __str__(self):
        return self.nombre

class AreaCompetencia(models.Model):
    area = models.ForeignKey(AreaCurricular, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    peso = models.DecimalField(max_digits=5, decimal_places=2)

class Periodo(models.Model):
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    anio_escolar = models.ForeignKey('core.AnioEscolar', on_delete=models.CASCADE)

    nombre = models.CharField(max_length=20)  # P1, P2...
    orden = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)
    es_completivo = models.BooleanField(default=False)
    # 🔒 NUEVO
    cerrado = models.BooleanField(default=False)
    fecha_cierre = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.nombre


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
    



class Calificacion(models.Model):
    inscripcion = models.ForeignKey(
        'estudiantes.Inscripcion',
        on_delete=models.CASCADE
    )

    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT)

    nota = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = (
            'inscripcion',
            'asignatura',
            'competencia',
            'periodo'
        )
