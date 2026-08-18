from django.contrib import admin

from .models import Tutor


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'cedula', 'parentesco', 'telefono', 'centro', 'estado')
    search_fields = ('primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido', 'cedula')
    list_filter = ('estado', 'parentesco', 'centro')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('estudiantes',)
