from django.contrib import admin

from .models import NotificacionAutomatica


@admin.register(NotificacionAutomatica)
class NotificacionAutomaticaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'total_destinatarios', 'campania', 'created_at')
    list_filter = ('tipo', 'centro', 'created_at')
    search_fields = ('titulo', 'centro__nombre')