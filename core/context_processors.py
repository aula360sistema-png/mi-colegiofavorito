# core/context_processors.py

from django.urls import reverse

from .models import ConfiguracionCentro
from core.utils.centro import obtener_centro_del_usuario
from core.cache_utils import obtener_o_generar, ttl

ROLES_ASISTENCIA = ('docente', 'secretaria', 'director', 'admin', 'superadmin')

ROLES_CAJA = ('director', 'admin', 'superadmin', 'cajero', 'secretaria')

ROLES_GESTION_CAJAS = ('director', 'admin', 'superadmin')

ROLES_CALIFICACIONES = ('docente', 'secretaria', 'director')

ROLES_NOMINA = ('director', 'admin', 'superadmin', 'secretaria')

ROLES_COMUNICACIONES = ('director', 'admin', 'superadmin', 'secretaria')


def obtener_configuracion_centro(centro_id):
    """Configuración del centro cacheada (se invalida al guardar el modelo)."""
    if not centro_id:
        return None
    return obtener_o_generar(
        f'config:{centro_id}',
        lambda: ConfiguracionCentro.objects.filter(centro_id=centro_id).first(),
        version=1,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


def modulos_sidebar(configuracion, request):

    if configuracion is None or not request.user.is_authenticated:
        return []

    rol = request.user.rol

    modulos = []

    if (
        configuracion.modulo_asistencia
        and (rol in ROLES_ASISTENCIA or request.user.is_superuser)
    ):
        links = [
            {
                'etiqueta': 'Asistencia estudiantes',
                'href': reverse('asistencia:tomar_asistencia'),
                'icono': 'fa-user-check',
            },
            {
                'etiqueta': 'Resumen de asistencia',
                'href': reverse('asistencia:resumen_asistencia'),
                'icono': 'fa-chart-line',
            },
            {
                'etiqueta': 'Días de no docencia',
                'href': reverse('asistencia:dias_no_docencia'),
                'icono': 'fa-calendar-xmark',
            },
        ]
        if configuracion.permitir_qr_asistencia:
            links.append({
                'etiqueta': 'Asistencia por QR',
                'href': reverse('asistencia:asistencia_qr_generar'),
                'icono': 'fa-qrcode',
            })
        if configuracion.usar_biometrico:
            links.append({
                'etiqueta': 'Asistencia biométrica',
                'href': reverse('asistencia:asistencia_biometrico'),
                'icono': 'fa-fingerprint',
            })
        modulos.append({
            'nombre': 'Asistencia',
            'id': 'menu-asistencia',
            'icono': 'fa-calendar-check',
            'links': links,
        })

    if configuracion.modulo_caja and (
        rol in ROLES_CAJA or request.user.is_superuser
    ):
        links = [
            {
                'etiqueta': 'Inicio de caja',
                'href': reverse('caja:caja_inicio'),
                'icono': 'fa-house',
            },
            {
                'etiqueta': 'Abrir / cerrar caja',
                'href': reverse('caja:caja_inicio') + '#apertura-cierre',
                'icono': 'fa-door-open',
            },
            {
                'etiqueta': 'Registrar pago (entrada)',
                'href': reverse('caja:registrar_pago'),
                'icono': 'fa-plus',
            },
            {
                'etiqueta': 'Registrar salida',
                'href': reverse('caja:registrar_egreso'),
                'icono': 'fa-minus',
            },
            {
                'etiqueta': 'Cuentas por cobrar',
                'href': reverse('caja:cuentas_por_cobrar'),
                'icono': 'fa-hand-holding-dollar',
            },
            {
                'etiqueta': 'Historial de pagos',
                'href': reverse('caja:lista_pagos'),
                'icono': 'fa-file-invoice-dollar',
            },
            {
                'etiqueta': 'Historial de salidas',
                'href': reverse('caja:lista_egresos'),
                'icono': 'fa-file-invoice',
            },
            {
                'etiqueta': 'Reporte diario',
                'href': reverse('caja:reporte_diario'),
                'icono': 'fa-chart-pie',
            },
            {
                'etiqueta': 'Aperturas y cierres',
                'href': reverse('caja:historial_sesiones'),
                'icono': 'fa-clock-rotate-left',
            },
            {
                'etiqueta': 'Conceptos',
                'href': reverse('caja:lista_conceptos'),
                'icono': 'fa-tags',
            },
            {
                'etiqueta': 'Asignar conceptos',
                'href': reverse('caja:asignaciones_conceptos'),
                'icono': 'fa-user-tag',
            },
        ]
        if rol in ROLES_GESTION_CAJAS:
            links.append({
                'etiqueta': 'Gestionar cajas',
                'href': reverse('caja:lista_cajas'),
                'icono': 'fa-cash-register',
            })
        modulos.append({
            'nombre': 'Caja',
            'id': 'menu-caja',
            'icono': 'fa-money-bill-wave',
            'links': links,
        })

    if configuracion.permitir_facturacion and (
        rol in ROLES_CAJA or request.user.is_superuser
    ):
        modulos.append({
            'nombre': 'Facturación',
            'id': 'menu-facturacion',
            'icono': 'fa-file-invoice-dollar',
            'links': [
                {
                    'etiqueta': 'Inicio de facturación',
                    'href': reverse('facturacion:facturacion_inicio'),
                    'icono': 'fa-house',
                },
                {
                    'etiqueta': 'Crear factura',
                    'href': reverse('facturacion:crear_factura'),
                    'icono': 'fa-plus',
                },
                {
                    'etiqueta': 'Facturas emitidas',
                    'href': reverse('facturacion:lista_facturas'),
                    'icono': 'fa-file-invoice',
                },
                {
                    'etiqueta': 'Secuencias NCF',
                    'href': reverse('facturacion:secuencias_ncf'),
                    'icono': 'fa-hashtag',
                },
                {
                    'etiqueta': 'Tipos de comprobante',
                    'href': reverse('facturacion:lista_comprobantes'),
                    'icono': 'fa-tags',
                },
            ],
        })

    if configuracion.modulo_nomina and (
        rol in ROLES_NOMINA or request.user.is_superuser
    ):
        modulos.append({
            'nombre': 'Nómina',
            'id': 'menu-nomina',
            'icono': 'fa-file-invoice-dollar',
            'links': [
                {
                    'etiqueta': 'Panel de nómina',
                    'href': reverse('nomina:dashboard'),
                    'icono': 'fa-chart-pie',
                },
                {
                    'etiqueta': 'Configuración',
                    'href': reverse('nomina:configuracion_nomina_list'),
                    'icono': 'fa-users-cog',
                },
                {
                    'etiqueta': 'Períodos de pago',
                    'href': reverse('nomina:periodo_nomina_list'),
                    'icono': 'fa-calendar-alt',
                },
                {
                    'etiqueta': 'Historial Nómina',
                    'href': reverse('nomina:historial_nomina'),
                    'icono': 'fa-clock-rotate-left',
                },
                {
                    'etiqueta': 'Cargos',
                    'href': reverse('nomina:cargo_list'),
                    'icono': 'fa-briefcase',
                },
                {
                    'etiqueta': 'AFP',
                    'href': reverse('nomina:afp_list'),
                    'icono': 'fa-building-columns',
                },
                {
                    'etiqueta': 'ARS',
                    'href': reverse('nomina:ars_list'),
                    'icono': 'fa-heart-pulse',
                },
                {
                    'etiqueta': 'Tipos de ingreso',
                    'href': reverse('nomina:tipo_ingreso_list'),
                    'icono': 'fa-coins',
                },
                {
                    'etiqueta': 'Tipos de descuento',
                    'href': reverse('nomina:tipo_descuento_list'),
                    'icono': 'fa-hand-holding-dollar',
                },
            ],
        })

    if request.user.rol in ROLES_CALIFICACIONES or request.user.is_superuser:
        links = []

        if request.user.rol == 'docente':
            links.append({
                'etiqueta': 'Mis asignaciones',
                'href': reverse('dashboard_docente'),
                'icono': 'fa-chalkboard-user',
            })
        else:
            links.append({
                'etiqueta': 'Seguimiento académico',
                'href': reverse('administracion:seguimiento_estudiantes'),
                'icono': 'fa-chart-line',
            })
            links.append({
                'etiqueta': 'Boletines oficiales',
                'href': reverse('administracion:lista_boletines'),
                'icono': 'fa-file-lines',
            })
            links.append({
                'etiqueta': 'Cierre y Promociones',
                'href': reverse('promociones:dashboard'),
                'icono': 'fa-graduation-cap',
            })

        modulos.append({
            'nombre': 'Calificaciones',
            'id': 'menu-calificaciones',
            'icono': 'fa-file-pen',
            'links': links,
        })

    if configuracion.modulo_mensajeria and (
        rol in ROLES_COMUNICACIONES or request.user.is_superuser
    ):
        modulos.append({
            'nombre': 'Comunicaciones',
            'id': 'menu-comunicaciones',
            'icono': 'fa-paper-plane',
            'links': [
                {
                    'etiqueta': 'Centro de correo',
                    'href': reverse('comunicaciones:campania_list'),
                    'icono': 'fa-envelope-open-text',
                },
                {
                    'etiqueta': 'Nueva campaña',
                    'href': reverse('comunicaciones:campania_create'),
                    'icono': 'fa-plus',
                },
            ],
        })

    if rol in ('director', 'admin', 'superadmin') or request.user.is_superuser:
        modulos.append({
            'nombre': 'Apariencia',
            'id': 'menu-apariencia',
            'icono': 'fa-palette',
            'links': [
                {
                    'etiqueta': 'Tema del centro',
                    'href': reverse('core:tema_centro'),
                    'icono': 'fa-brush',
                },
                {
                    'etiqueta': 'Logo del centro',
                    'href': reverse('core:logo_centro'),
                    'icono': 'fa-image',
                },
            ],
        })

    return modulos


def configuracion_centro(request):

    centro_id = request.session.get('centro_id')

    configuracion = None

    if centro_id:
        configuracion = obtener_configuracion_centro(centro_id)

    if configuracion is None and request.user.is_authenticated:

        centro = obtener_centro_del_usuario(request)

        if centro:
            configuracion = obtener_configuracion_centro(centro.id)

            if configuracion is not None:
                request.session['centro_id'] = centro.id
                centro_id = centro.id

    modulos = []
    if request.user.is_authenticated:
        clave_sidebar = (
            f'sidebar:{centro_id or 0}:{request.user.pk}:'
            f'{request.user.rol or "sin_rol"}'
        )
        modulos = obtener_o_generar(
            clave_sidebar,
            lambda: modulos_sidebar(configuracion, request),
            version=1,
            timeout=ttl('CACHE_TTL_CORTO'),
        )

    # Tema y logo del centro
    tema_centro = None
    centro_logo = None
    centro_nombre = None
    if centro_id:
        from .models import TemaCentro, CentroEducativo
        centro_obj = CentroEducativo.objects.filter(id=centro_id).first()
        if centro_obj:
            centro_nombre = centro_obj.nombre
            if centro_obj.logo:
                centro_logo = centro_obj.logo.url
            tema_centro = TemaCentro.objects.filter(centro_id=centro_id).first()

    return {
        'configuracion': configuracion,
        'modulos_sidebar': modulos,
        'tema_centro': tema_centro,
        'centro_logo': centro_logo,
        'centro_nombre': centro_nombre,
    }