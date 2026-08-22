from django.contrib import admin

from .models import ConsentimientoInformado, RegistroAccesoDato, RegistroRetencion


@admin.register(ConsentimientoInformado)
class ConsentimientoInformadoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'tutor_nombre', 'fecha_firma', 'activo')
    list_filter = ('activo', 'fecha_firma')
    search_fields = ('estudiante__primer_nombre', 'estudiante__primer_apellido', 'tutor_nombre')


@admin.register(RegistroAccesoDato)
class RegistroAccesoDatoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_dato', 'accion', 'fecha', 'ip')
    list_filter = ('tipo_dato', 'accion', 'fecha')
    search_fields = ('usuario__username', 'estudiante__primer_nombre')
    readonly_fields = ('usuario', 'tipo_dato', 'accion', 'descripcion', 'estudiante',
                       'ip', 'user_agent', 'fecha')


@admin.register(RegistroRetencion)
class RegistroRetencionAdmin(admin.ModelAdmin):
    list_display = ('tipo_dato', 'accion', 'registros_afectados', 'fecha_ejecucion')
    list_filter = ('tipo_dato', 'accion')
    readonly_fields = ('tipo_dato', 'accion', 'registros_afectados', 'detalle', 'fecha_ejecucion')
