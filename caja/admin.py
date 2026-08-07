from django.contrib import admin

from .models import (
    AsignacionConcepto,
    Caja,
    ConceptoPago,
    Egreso,
    Pago,
    SesionCaja,
)


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'centro', 'activa', 'created_at')
    list_filter = ('activa', 'centro')
    search_fields = ('nombre',)


@admin.register(ConceptoPago)
class ConceptoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'monto', 'es_recurrente', 'activo', 'centro')
    list_filter = ('activo', 'es_recurrente')
    search_fields = ('nombre',)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('recibo', 'estudiante', 'concepto', 'monto', 'metodo_pago', 'fecha', 'sesion')
    list_filter = ('metodo_pago', 'fecha', 'sesion')
    search_fields = ('estudiante__matricula', 'estudiante__primer_nombre', 'estudiante__primer_apellido')


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    list_display = ('recibo', 'concepto', 'beneficiario', 'monto', 'metodo_pago', 'fecha', 'sesion')
    list_filter = ('metodo_pago', 'fecha')
    search_fields = ('concepto', 'beneficiario')


@admin.register(SesionCaja)
class SesionCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'caja', 'centro', 'fecha_apertura', 'fecha_cierre', 'estado', 'monto_inicial', 'arqueo', 'diferencia')
    list_filter = ('estado', 'centro')
    readonly_fields = ('diferencia',)


@admin.register(AsignacionConcepto)
class AsignacionConceptoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'concepto', 'anio_escolar', 'activo')
    list_filter = ('activo', 'anio_escolar')
    search_fields = ('estudiante__matricula', 'estudiante__primer_nombre')
