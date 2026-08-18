from django.contrib import admin

from .models import Factura, FacturaItem, SecuenciaNCF, TipoComprobante


class FacturaItemInline(admin.TabularInline):
    model = FacturaItem
    extra = 0


@admin.register(TipoComprobante)
class TipoComprobanteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'letra', 'activo')
    list_editable = ('activo',)
    search_fields = ('codigo', 'nombre')


@admin.register(SecuenciaNCF)
class SecuenciaNCFAdmin(admin.ModelAdmin):
    list_display = ('centro', 'tipo', 'ultimo_numero', 'activo')
    list_filter = ('centro', 'tipo')


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        'ncf', 'fecha', 'estudiante', 'tipo', 'subtotal', 'itbis', 'total'
    )
    list_filter = ('centro', 'tipo', 'aplica_itbis')
    search_fields = ('ncf', 'estudiante__primer_nombre', 'estudiante__primer_apellido')
    readonly_fields = (
        'ncf', 'subtotal', 'itbis', 'total', 'fecha', 'creado_por'
    )
    inlines = [FacturaItemInline]
