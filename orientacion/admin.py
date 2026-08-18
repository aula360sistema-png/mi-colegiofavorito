from django.contrib import admin

from .models import AlertaEstudiante, IntervencionPsicopedagogica, PlanPedagogico


@admin.register(AlertaEstudiante)
class AlertaEstudianteAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'tipo', 'severidad', 'estado', 'fecha', 'atendida_por')
    list_filter = ('tipo', 'severidad', 'estado', 'anio_escolar')
    search_fields = ('estudiante__primer_nombre', 'estudiante__primer_apellido', 'descripcion')


@admin.register(PlanPedagogico)
class PlanPedagogicoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'tipo', 'origen', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('tipo', 'origen', 'estado', 'anio_escolar')


@admin.register(IntervencionPsicopedagogica)
class IntervencionPsicopedagogicaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'fecha', 'tipo', 'orientador', 'objetivo')
    list_filter = ('tipo',)
