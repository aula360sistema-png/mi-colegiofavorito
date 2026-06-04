from django.contrib import admin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'rol', 'fecha_creacion')
    list_filter = ('is_active',)   # ← COMA OBLIGATORIA
    search_fields = ('username', 'email', 'nombre', 'apellido', 'rol', 'fecha_creacion') 



