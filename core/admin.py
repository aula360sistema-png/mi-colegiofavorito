from django.contrib import admin
from core.models import (
    CentroEducativo, AnioEscolar, RolCentro, UsuarioCentro,
    ConfiguracionCentro, Proveedor, CentroProveedor
)
from estudiantes.models import Estudiante, HistorialAcademico, Inscripcion
from docentes.models import Docente, AsignacionDocente
from academico.models import (
    Nivel, Grado, Seccion, AreaCurricular, Asignatura,
    GradoAsignatura, Competencia, AreaCompetencia, Periodo,
    Calificacion, DocenteMateria
)

# -------------------
# Inlines
# -------------------

class HistorialAcademicoInline(admin.TabularInline):
    model = HistorialAcademico
    extra = 0
    fields = ('nivel', 'grado', 'seccion', 'anio_escolar', 'estado')
    readonly_fields = ('created_at',)

class InscripcionInline(admin.TabularInline):
    model = Inscripcion
    extra = 0
    fields = ('centro', 'anio_escolar', 'grado', 'seccion', 'fecha')
    readonly_fields = ('fecha',)

class GradoAsignaturaInline(admin.TabularInline):
    model = GradoAsignatura
    extra = 0

class AsignacionDocenteInline(admin.TabularInline):
    model = AsignacionDocente
    extra = 0

class DocenteMateriaInline(admin.TabularInline):
    model = DocenteMateria
    extra = 0

class CalificacionInline(admin.TabularInline):
    model = Calificacion
    extra = 0

# -------------------
# Core / Centros
# -------------------
@admin.register(CentroEducativo)
class CentroEducativoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_minerd', 'activo', 'fecha_creacion')
    search_fields = ('nombre', 'codigo_minerd')
    list_filter = ('activo',)

@admin.register(AnioEscolar)
class AnioEscolarAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro', 'fecha_inicio', 'fecha_fin', 'activo')
    search_fields = ('nombre', 'centro__nombre')
    list_filter = ('centro', 'activo')

@admin.register(RolCentro)
class RolCentroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')

@admin.register(UsuarioCentro)
class UsuarioCentroAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'centro', 'rol', 'activo', 'fecha_asignacion')
    search_fields = ('usuario__username', 'usuario__email', 'centro__nombre')
    list_filter = ('centro', 'rol', 'activo')

@admin.register(ConfiguracionCentro)
class ConfiguracionCentroAdmin(admin.ModelAdmin):
    list_display = (
        'centro', 'usa_calificacion_numerica',
        'nota_minima_aprobacion', 'usa_competencias', 'permite_completivo'
    )
    list_filter = ('usa_calificacion_numerica', 'usa_competencias', 'permite_completivo')

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'activo')
    search_fields = ('nombre', 'email')
    list_filter = ('activo',)

@admin.register(CentroProveedor)
class CentroProveedorAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'centro')
    list_filter = ('proveedor', 'centro')


# -------------------
# Estudiantes
# -------------------
@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_completo', 'matricula', 'centro',
        'sexo', 'estado', 'created_at'
    )
    search_fields = (
        'primer_nombre', 'segundo_nombre',
        'primer_apellido', 'segundo_apellido',
        'matricula', 'nombre_tutor'
    )
    list_filter = ('centro', 'sexo', 'estado')
    inlines = [HistorialAcademicoInline, InscripcionInline]  # <- inlines aquí


# -------------------
# Docentes
# -------------------
@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_completo', 'cedula', 'centro', 
        'sexo', 'tipo_contrato', 'tanda', 'estado', 'fecha_ingreso'
    )
    search_fields = (
        'primer_nombre', 'segundo_nombre', 
        'primer_apellido', 'segundo_apellido',
        'cedula', 'codigo_docente_minerd'
    )
    list_filter = ('centro', 'sexo', 'tipo_contrato', 'tanda', 'estado')
    inlines = [AsignacionDocenteInline, DocenteMateriaInline]


# -------------------
# Académico / Asignaturas
# -------------------
@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro')
    search_fields = ('nombre', 'centro__nombre')
    list_filter = ('centro',)

@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nivel')
    search_fields = ('nombre', 'nivel__nombre')
    list_filter = ('nivel__centro',)
    inlines = [GradoAsignaturaInline]

@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'grado')
    search_fields = ('nombre', 'grado__nombre')
    list_filter = ('grado__nivel__centro',)

@admin.register(AreaCurricular)
class AreaCurricularAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro')
    search_fields = ('nombre',)
    list_filter = ('centro',)

@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro', 'area')
    search_fields = ('nombre',)
    list_filter = ('centro', 'area')

@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(AreaCompetencia)
class AreaCompetenciaAdmin(admin.ModelAdmin):
    list_display = ('area', 'competencia', 'peso')
    list_filter = ('area__centro',)
    search_fields = ('area__nombre', 'competencia__nombre')

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro', 'anio_escolar', 'orden', 'activo', 'es_completivo')
    list_filter = ('centro', 'anio_escolar', 'activo', 'es_completivo')
    search_fields = ('nombre',)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'asignatura', 'competencia', 'periodo', 'nota')
    list_filter = ('asignatura', 'competencia', 'periodo', 'inscripcion__centro')
    search_fields = ('inscripcion__estudiante__primer_nombre', 'inscripcion__estudiante__primer_apellido')

@admin.register(DocenteMateria)
class DocenteMateriaAdmin(admin.ModelAdmin):
    list_display = ('docente', 'asignatura', 'grado', 'seccion', 'anio_escolar')
    list_filter = ('grado', 'seccion', 'anio_escolar', 'asignatura')
    search_fields = ('docente__primer_nombre', 'docente__primer_apellido', 'asignatura__nombre')
