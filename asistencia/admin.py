from django.contrib import admin

from .models import AsistenciaEstudiante, DiaNoDocencia


@admin.register(DiaNoDocencia)
class DiaNoDocenciaAdmin(admin.ModelAdmin):
    list_display = (
        'fecha',
        'motivo',
        'anio_escolar',
        'centro',
        'registrado_por',
    )
    list_filter = ('anio_escolar', 'centro')
    search_fields = ('motivo',)
    date_hierarchy = 'fecha'


@admin.register(AsistenciaEstudiante)
class AsistenciaEstudianteAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'fecha', 'estado', 'registrada_por')
    list_filter = ('estado', 'fecha')
    search_fields = (
        'inscripcion__estudiante__primer_nombre',
        'inscripcion__estudiante__matricula',
    )
