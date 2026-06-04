from django.urls import path

from . import views

app_name = 'nomina'

urlpatterns = [

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


    # ==========================
    # PERIODOS
    # ==========================

    path(
        'periodos/',
        views.periodo_nomina_list,
        name='periodo_nomina_list'
    ),


    # ==========================
    # GENERAR NOMINA
    # ==========================

    path(
        'generar/<int:periodo_id>/',
        views.generar_nomina_view,
        name='generar_nomina'
    ),


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