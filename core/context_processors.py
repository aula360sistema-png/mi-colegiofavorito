# core/context_processors.py

from django.urls import reverse

from .models import ConfiguracionCentro
from core.utils.centro import obtener_centro_del_usuario

ROLES_ADMIN = ('director', 'admin', 'superadmin')

ROLES_ASISTENCIA = ('docente', 'secretaria', 'director', 'admin', 'superadmin')

ROLES_CAJA = ('director', 'admin', 'superadmin', 'cajero')

ROLES_GESTION_CAJAS = ('director', 'admin', 'superadmin')


def modulos_sidebar(configuracion, request):

    if configuracion is None or not request.user.is_authenticated:
        return []

    rol = request.user.rol
    es_admin = rol in ROLES_ADMIN or request.user.is_superuser

    modulos = []

    if (
        configuracion.modulo_asistencia
        and (rol in ROLES_ASISTENCIA or request.user.is_superuser)
    ):
        modulos.append({
            'nombre': 'Asistencia',
            'id': 'menu-asistencia',
            'icono': 'fa-calendar-check',
            'links': [
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
            ],
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

    if configuracion.modulo_nomina and es_admin:
        modulos.append({
            'nombre': 'Nómina',
            'id': 'menu-nomina',
            'icono': 'fa-file-invoice-dollar',
            'links': [
                {
                    'etiqueta': 'Configuración',
                    'href': reverse('nomina:configuracion_nomina_list'),
                    'icono': 'fa-users-cog',
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
                    'etiqueta': 'Períodos de pago',
                    'href': reverse('nomina:periodo_nomina_list'),
                    'icono': 'fa-calendar-alt',
                },
                {
                    'etiqueta': 'Historial Nómina',
                    'href': reverse('nomina:historial_nomina'),
                    'icono': 'fa-clock-rotate-left',
                },
            ],
        })

    return modulos


def configuracion_centro(request):

    centro_id = request.session.get('centro_id')

    configuracion = None

    if centro_id:

        try:

            configuracion = ConfiguracionCentro.objects.get(
                centro_id=centro_id
            )

        except ConfiguracionCentro.DoesNotExist:
            pass

    if configuracion is None and request.user.is_authenticated:

        centro = obtener_centro_del_usuario(request)

        if centro:

            configuracion = getattr(
                centro,
                'configuracioncentro',
                None,
            )

    return {
        'configuracion': configuracion,
        'modulos_sidebar': modulos_sidebar(configuracion, request),
    }