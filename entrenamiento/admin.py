from django.contrib import admin

from .models import (
    DestrezaCognitiva,
    DiagnosticoCognitivo,
    Ejercicio,
    IntentoEjercicio,
    ItemPlanRefuerzo,
    MetricaCognitiva,
    PlanRefuerzo,
    SesionEntrenamiento,
    TramoEdad,
    UnidadEntrenamiento,
)


@admin.register(TramoEdad)
class TramoEdadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edad_min', 'edad_max', 'orden', 'activo')
    list_editable = ('orden', 'activo')
    ordering = ('edad_min',)


@admin.register(DestrezaCognitiva)
class DestrezaCognitivaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tramo', 'categoria', 'orden', 'activo')
    list_filter = ('tramo', 'categoria', 'activo')
    list_editable = ('orden', 'activo')


@admin.register(UnidadEntrenamiento)
class UnidadEntrenamientoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nombre', 'tramo', 'activo')
    list_filter = ('tramo', 'activo')
    list_editable = ('activo',)
    filter_horizontal = ('destrezas',)


@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    list_display = ('enunciado', 'unidad', 'destreza', 'tipo', 'dificultad', 'activo')
    list_filter = ('unidad', 'destreza', 'tipo', 'dificultad', 'activo')


@admin.register(DiagnosticoCognitivo)
class DiagnosticoCognitivoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'anio_escolar', 'tramo', 'fecha', 'ipd')
    list_filter = ('anio_escolar', 'tramo')


@admin.register(SesionEntrenamiento)
class SesionEntrenamientoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'unidad', 'estado', 'aciertos', 'errores', 'ipd', 'fecha_inicio')
    list_filter = ('estado', 'anio_escolar')


@admin.register(IntentoEjercicio)
class IntentoEjercicioAdmin(admin.ModelAdmin):
    list_display = ('sesion', 'ejercicio', 'acierto', 'tiempo_respuesta_ms', 'dificultad_aplicada')
    list_filter = ('acierto', 'dificultad_aplicada')


@admin.register(MetricaCognitiva)
class MetricaCognitivaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'periodo', 'tramo', 'ipd', 'percentil_edad', 'fecha_corte')
    list_filter = ('anio_escolar', 'tramo')


class ItemPlanRefuerzoInline(admin.TabularInline):
    model = ItemPlanRefuerzo
    extra = 0


@admin.register(PlanRefuerzo)
class PlanRefuerzoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'unidad', 'origen', 'generado_por', 'estado', 'fecha_generado')
    list_filter = ('origen', 'generado_por', 'estado', 'anio_escolar')
    inlines = (ItemPlanRefuerzoInline,)
