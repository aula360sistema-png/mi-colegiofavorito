from django.contrib import admin

from .models import Campania, DestinatarioCampania, NotificacionPago


class DestinatarioInline(admin.TabularInline):
    model = DestinatarioCampania
    extra = 0
    readonly_fields = ('tutor', 'canal', 'contacto', 'estado', 'error', 'enviado_at')


@admin.register(Campania)
class CampaniaAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'canal', 'alcance', 'estado', 'total_destinatarios', 'created_at')
    list_filter = ('canal', 'alcance', 'estado', 'centro')
    search_fields = ('asunto', 'mensaje', 'centro__nombre')
    readonly_fields = ('enviado_at', 'created_at', 'updated_at')
    inlines = [DestinatarioInline]


@admin.register(NotificacionPago)
class NotificacionPagoAdmin(admin.ModelAdmin):
    list_display = ('pago', 'tutor', 'canal', 'contacto', 'estado', 'created_at')
    list_filter = ('canal', 'estado', 'centro')
    search_fields = ('tutor__primer_nombre', 'tutor__primer_apellido', 'pago__recibo')
