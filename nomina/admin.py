from django.contrib import admin

from .models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    TipoIngreso,
    TipoDescuento,
    IngresoEmpleado,
    DescuentoEmpleado,
    PeriodoNomina,
    Nomina,
    IngresoNomina,
    DescuentoNomina,
)


# =====================================================
# AFP
# =====================================================

@admin.register(AFP)
class AFPAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'porcentaje_empleado',
        'porcentaje_empresa',
        'activo',
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'activo',
    )


# =====================================================
# ARS
# =====================================================

@admin.register(ARS)
class ARSAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'porcentaje_empleado',
        'porcentaje_empresa',
        'activo',
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'activo',
    )


# =====================================================
# CARGOS
# =====================================================

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'activo',
        'fecha_creacion',
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'activo',
    )


# =====================================================
# CONFIGURACION NOMINA
# =====================================================

@admin.register(ConfiguracionNomina)
class ConfiguracionNominaAdmin(admin.ModelAdmin):

    list_display = (
        'usuario',
        'centro',
        'cargo',
        'salario_base',
        'afp',
        'ars',
        'activo_nomina',
    )

    search_fields = (
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
    )

    list_filter = (
        'activo_nomina',
        'centro',
        'cargo',
        'afp',
        'ars',
    )


# =====================================================
# TIPOS INGRESOS
# =====================================================

@admin.register(TipoIngreso)
class TipoIngresoAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'obligatorio',
        'activo',
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'obligatorio',
        'activo',
    )


# =====================================================
# TIPOS DESCUENTOS
# =====================================================

@admin.register(TipoDescuento)
class TipoDescuentoAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'porcentaje',
        'es_porcentaje',
        'obligatorio',
        'activo',
    )

    search_fields = (
        'nombre',
    )

    list_filter = (
        'es_porcentaje',
        'obligatorio',
        'activo',
    )


# =====================================================
# INGRESOS EMPLEADO
# =====================================================

@admin.register(IngresoEmpleado)
class IngresoEmpleadoAdmin(admin.ModelAdmin):

    list_display = (
        'configuracion',
        'tipo',
        'monto',
        'activo',
    )

    search_fields = (
        'configuracion__usuario__username',
        'tipo__nombre',
    )

    list_filter = (
        'activo',
        'tipo',
    )


# =====================================================
# DESCUENTOS EMPLEADO
# =====================================================

@admin.register(DescuentoEmpleado)
class DescuentoEmpleadoAdmin(admin.ModelAdmin):

    list_display = (
        'configuracion',
        'tipo',
        'monto',
        'activo',
    )

    search_fields = (
        'configuracion__usuario__username',
        'tipo__nombre',
    )

    list_filter = (
        'activo',
        'tipo',
    )


# =====================================================
# PERIODOS NOMINA
# =====================================================

@admin.register(PeriodoNomina)
class PeriodoNominaAdmin(admin.ModelAdmin):

    list_display = (
        'descripcion',
        'centro',
        'anio',
        'mes',
        'numero_periodo',
        'fecha_pago',
        'cerrado',
        'nomina_generada',
    )

    search_fields = (
        'descripcion',
    )

    list_filter = (
        'centro',
        'anio',
        'mes',
        'cerrado',
        'nomina_generada',
    )


# =====================================================
# NOMINA
# =====================================================

@admin.register(Nomina)
class NominaAdmin(admin.ModelAdmin):

    list_display = (
        'usuario',
        'periodo',
        'salario_base',
        'total_ingresos',
        'total_descuentos',
        'neto_pagar',
        'estado',
        'pagado',
    )

    search_fields = (
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
    )

    list_filter = (
        'estado',
        'pagado',
        'periodo',
    )


# =====================================================
# INGRESOS NOMINA
# =====================================================

@admin.register(IngresoNomina)
class IngresoNominaAdmin(admin.ModelAdmin):

    list_display = (
        'nomina',
        'tipo',
        'monto',
    )

    search_fields = (
        'tipo__nombre',
    )

    list_filter = (
        'tipo',
    )


# =====================================================
# DESCUENTOS NOMINA
# =====================================================

@admin.register(DescuentoNomina)
class DescuentoNominaAdmin(admin.ModelAdmin):

    list_display = (
        'nomina',
        'tipo',
        'monto',
    )

    search_fields = (
        'tipo__nombre',
    )

    list_filter = (
        'tipo',
    )