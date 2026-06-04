from django.contrib import admin
from django.utils.html import format_html
from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):

    list_display = (
        'fecha',
        'usuario',
        'accion_color',
        'riesgo_color',
        'modulo',
        'modelo',
        'objeto_id',
        'ip',
        'tipo_dispositivo',
    )

    list_filter = (
        'accion',
        'riesgo',
        'modulo',
        'modelo',
        'tipo_dispositivo',
        'fecha',
    )

    search_fields = (
        'usuario__username',
        'descripcion',
        'modelo',
        'objeto_id',
        'ip',
        'ruta',
    )

    readonly_fields = (
        'usuario',
        'accion',
        'modulo',
        'descripcion',
        'modelo',
        'objeto_id',
        'ip',
        'ruta',
        'metodo',
        'navegador',
        'tipo_dispositivo',
        'riesgo',
        'datos_anteriores',
        'datos_nuevos',
        'fecha',
    )

    ordering = ('-fecha',)

    list_per_page = 50

    fieldsets = (

        ('Información General', {
            'fields': (
                'usuario',
                'accion',
                'riesgo',
                'modulo',
                'descripcion',
            )
        }),

        ('Objeto Afectado', {
            'fields': (
                'modelo',
                'objeto_id',
            )
        }),

        ('Conexión', {
            'fields': (
                'ip',
                'ruta',
                'metodo',
                'tipo_dispositivo',
                'navegador',
            )
        }),

        ('Snapshots', {
            'fields': (
                'datos_anteriores',
                'datos_nuevos',
            )
        }),

        ('Fecha', {
            'fields': (
                'fecha',
            )
        }),
    )

    # Bloquear agregar manual
    def has_add_permission(self, request):
        return False

    # Bloquear eliminar
    def has_delete_permission(self, request, obj=None):
        return False

    # Acción con color
    def accion_color(self, obj):

        colores = {
            'CREAR': 'green',
            'EDITAR': 'orange',
            'ELIMINAR': 'red',
            'LOGIN': 'blue',
            'LOGOUT': 'gray',
            'LOGIN_FAILED': '#8B0000',
        }

        color = colores.get(obj.accion, 'black')

        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            obj.accion
        )

    accion_color.short_description = "Acción"

    # Riesgo con color
    def riesgo_color(self, obj):

        colores = {
            'BAJO': 'green',
            'MEDIO': 'orange',
            'ALTO': 'red',
            'CRITICO': '#8B0000',
        }

        color = colores.get(obj.riesgo, 'black')

        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            obj.riesgo
        )

    riesgo_color.short_description = "Riesgo"