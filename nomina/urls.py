from django.urls import path

from . import views

app_name = 'nomina'

urlpatterns = [

    # ==========================
    # DASHBOARD
    # ==========================

    path(
        '',
        views.dashboard,
        name='dashboard'
    ),

    # ==========================
    # AFP
    # ==========================

    path(
        'afp/',
        views.afp_list,
        name='afp_list'
    ),

    path(
        'afp/crear/',
        views.afp_create,
        name='afp_create'
    ),

    path(
        'afp/<int:pk>/editar/',
        views.afp_edit,
        name='afp_edit'
    ),

    path(
        'afp/<int:pk>/alternar/',
        views.afp_toggle,
        name='afp_toggle'
    ),

    # ==========================
    # ARS
    # ==========================

    path(
        'ars/',
        views.ars_list,
        name='ars_list'
    ),

    path(
        'ars/crear/',
        views.ars_create,
        name='ars_create'
    ),

    path(
        'ars/<int:pk>/editar/',
        views.ars_edit,
        name='ars_edit'
    ),

    path(
        'ars/<int:pk>/alternar/',
        views.ars_toggle,
        name='ars_toggle'
    ),

    # ==========================
    # CARGOS
    # ==========================

    path(
        'cargos/',
        views.cargo_list,
        name='cargo_list'
    ),

    path(
        'cargos/crear/',
        views.cargo_create,
        name='cargo_create'
    ),

    path(
        'cargos/<int:pk>/editar/',
        views.cargo_edit,
        name='cargo_edit'
    ),

    path(
        'cargos/<int:pk>/alternar/',
        views.cargo_toggle,
        name='cargo_toggle'
    ),

    # ==========================
    # TIPOS DE INGRESO
    # ==========================

    path(
        'tipos-ingreso/',
        views.tipo_ingreso_list,
        name='tipo_ingreso_list'
    ),

    path(
        'tipos-ingreso/crear/',
        views.tipo_ingreso_create,
        name='tipo_ingreso_create'
    ),

    path(
        'tipos-ingreso/<int:pk>/alternar/',
        views.tipo_ingreso_toggle,
        name='tipo_ingreso_toggle'
    ),

    # ==========================
    # TIPOS DE DESCUENTO
    # ==========================

    path(
        'tipos-descuento/',
        views.tipo_descuento_list,
        name='tipo_descuento_list'
    ),

    path(
        'tipos-descuento/crear/',
        views.tipo_descuento_create,
        name='tipo_descuento_create'
    ),

    path(
        'tipos-descuento/<int:pk>/alternar/',
        views.tipo_descuento_toggle,
        name='tipo_descuento_toggle'
    ),

    # ==========================
    # CONFIGURACION NOMINA
    # ==========================

    path(
        'configuracion/',
        views.configuracion_nomina_list,
        name='configuracion_nomina_list'
    ),

    path(
        'configuracion/crear/',
        views.configuracion_nomina_create,
        name='configuracion_nomina_create'
    ),

    path(
        'configuracion/<int:pk>/editar/',
        views.configuracion_nomina_edit,
        name='configuracion_nomina_edit'
    ),

    path(
        'configuracion/<int:pk>/alternar/',
        views.configuracion_nomina_toggle,
        name='configuracion_nomina_toggle'
    ),

    path(
        'configuracion/<int:pk>/eliminar/',
        views.configuracion_nomina_delete,
        name='configuracion_nomina_delete'
    ),

    # ==========================
    # EMPLEADO DETALLE
    # ==========================

    path(
        'empleado/<int:pk>/',
        views.empleado_detalle,
        name='empleado_detalle'
    ),

    path(
        'empleado/<int:pk>/ingreso/',
        views.ingreso_empleado_create,
        name='ingreso_empleado_create'
    ),

    path(
        'empleado/<int:pk>/ingreso/<int:ingreso_id>/eliminar/',
        views.ingreso_empleado_delete,
        name='ingreso_empleado_delete'
    ),

    path(
        'empleado/<int:pk>/descuento/',
        views.descuento_empleado_create,
        name='descuento_empleado_create'
    ),

    path(
        'empleado/<int:pk>/descuento/<int:descuento_id>/eliminar/',
        views.descuento_empleado_delete,
        name='descuento_empleado_delete'
    ),

    # ==========================
    # PERIODOS
    # ==========================

    path(
        'periodos/',
        views.periodo_nomina_list,
        name='periodo_nomina_list'
    ),

    path(
        'periodos/<int:periodo_id>/',
        views.periodo_detalle,
        name='periodo_detalle'
    ),

    # ==========================
    # ACCIONES DE PERIODO
    # ==========================

    path(
        'generar/<int:periodo_id>/',
        views.generar_nomina_view,
        name='generar_nomina'
    ),

    path(
        'periodos/<int:periodo_id>/cerrar/',
        views.periodo_cerrar,
        name='periodo_cerrar'
    ),

    path(
        'periodos/<int:periodo_id>/anular/',
        views.periodo_anular,
        name='periodo_anular'
    ),

    # ==========================
    # NOMINA INDIVIDUAL
    # ==========================

    path(
        'nomina/<int:nomina_id>/estado/',
        views.nomina_estado,
        name='nomina_estado'
    ),

    path(
        'nomina/<int:nomina_id>/boleta/',
        views.boleta_pago,
        name='boleta_pago'
    ),

    # ==========================
    # HISTORIAL
    # ==========================

    path(
        'historial/',
        views.historial_nomina,
        name='historial_nomina'
    ),

    path(
        'detalle/<int:periodo_id>/',
        views.detalle_nomina_view,
        name='detalle_nomina'
    ),
]
