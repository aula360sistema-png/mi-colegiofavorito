from django.urls import path

from . import views

app_name = 'facturacion'

urlpatterns = [
    path('', views.facturacion_inicio, name='facturacion_inicio'),
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path(
        'facturas/crear/',
        views.crear_factura,
        name='crear_factura'
    ),
    path(
        'facturas/<int:factura_id>/',
        views.detalle_factura,
        name='detalle_factura'
    ),
    path('comprobantes/', views.lista_comprobantes, name='lista_comprobantes'),
    path('secuencias-ncf/', views.secuencias_ncf, name='secuencias_ncf'),
]
