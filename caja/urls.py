from django.urls import path

from . import views

app_name = 'caja'

urlpatterns = [
    path('', views.caja_inicio, name='caja_inicio'),
    path('cajas/', views.lista_cajas, name='lista_cajas'),
    path('cajas/nueva/', views.crear_caja, name='crear_caja'),
    path('cajas/<int:caja_id>/editar/', views.editar_caja, name='editar_caja'),
    path('cajas/<int:caja_id>/alternar/', views.alternar_caja, name='alternar_caja'),
    path('apertura/', views.abrir_caja, name='abrir_caja'),
    path('cierre/', views.cerrar_caja, name='cerrar_caja'),
    path('pagos/', views.lista_pagos, name='lista_pagos'),
    path('pagos/nuevo/', views.registrar_pago, name='registrar_pago'),
    path(
        'pagos/nuevo/<int:estudiante_id>/',
        views.registrar_pago,
        name='registrar_pago_estudiante'
    ),
    path(
        'pagos/nuevo/<int:estudiante_id>/<int:concepto_id>/',
        views.registrar_pago,
        name='registrar_pago_estudiante_concepto'
    ),
    path('pagos/<int:pago_id>/recibo/', views.recibo_pago, name='recibo_pago'),
    path(
        'pagos/balance/<int:estudiante_id>/',
        views.api_balance_pago,
        name='api_balance_pago'
    ),
    path('egresos/', views.lista_egresos, name='lista_egresos'),
    path('egresos/nuevo/', views.registrar_egreso, name='registrar_egreso'),
    path('conceptos/', views.lista_conceptos, name='lista_conceptos'),
    path('conceptos/nuevo/', views.crear_concepto, name='crear_concepto'),
    path('cuentas/', views.cuentas_por_cobrar, name='cuentas_por_cobrar'),
    path(
        'asignaciones/',
        views.asignaciones_conceptos,
        name='asignaciones_conceptos'
    ),
    path('reporte/', views.reporte_diario, name='reporte_diario'),
    path('sesiones/', views.historial_sesiones, name='historial_sesiones'),
    path(
        'sesiones/<int:sesion_id>/',
        views.detalle_sesion,
        name='detalle_sesion'
    ),
]
