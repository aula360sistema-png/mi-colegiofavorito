import logging

from datetime import date

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.decorators import centro_required, role_required

from nomina.services import (
    ESTADOS_ACTIVOS,
    MESES,
    anular_nomina,
    datos_boleta_pago,
    datos_periodo_detalle,
    enviar_notificaciones_nomina,
    generar_nomina,
    generar_periodos_si_no_existen,
    historial_nomina as historial_nomina_cached,
    metricas_dashboard,
)

from .models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    DescuentoEmpleado,
    IngresoEmpleado,
    Nomina,
    PeriodoNomina,
    TipoDescuento,
    TipoIngreso,
)

from .forms import (
    AFPForm,
    ARSForm,
    CargoForm,
    ConfiguracionNominaForm,
    DescuentoEmpleadoForm,
    IngresoEmpleadoForm,
    TipoDescuentoForm,
    TipoIngresoForm,
)

logger = logging.getLogger(__name__)

ROLES_NOMINA = ('director', 'admin', 'superadmin', 'secretaria')

ESTADO_LABELS = dict(Nomina.ESTADOS)


# ==========================================
# DASHBOARD
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def dashboard(request):
    centro = request.centro

    datos = metricas_dashboard(centro)

    return render(request, 'nomina/dashboard.html', {
        'centro': centro,
        'meses': MESES,
        **datos,
    })


# ==========================================
# CARGOS
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def cargo_list(request):
    cargos = Cargo.objects.all().order_by('nombre')
    return render(request, 'nomina/cargo_list.html', {'cargos': cargos})


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def cargo_create(request):
    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cargo creado correctamente')
            return redirect('nomina:cargo_list')
    else:
        form = CargoForm()
    return render(request, 'nomina/cargo_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def cargo_edit(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    if request.method == 'POST':
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cargo actualizado correctamente')
            return redirect('nomina:cargo_list')
    else:
        form = CargoForm(instance=cargo)
    return render(request, 'nomina/cargo_form.html', {
        'form': form,
        'accion': 'Editar',
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def cargo_toggle(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    cargo.activo = not cargo.activo
    cargo.save()
    estado = 'activado' if cargo.activo else 'desactivado'
    messages.success(request, f"Cargo '{cargo.nombre}' {estado}.")
    return redirect('nomina:cargo_list')


# ==========================================
# AFP
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def afp_list(request):
    afps = AFP.objects.all().order_by('nombre')
    return render(request, 'nomina/afp_list.html', {'afps': afps})


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def afp_create(request):
    if request.method == 'POST':
        form = AFPForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'AFP creada correctamente')
            return redirect('nomina:afp_list')
    else:
        form = AFPForm()
    return render(request, 'nomina/afp_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def afp_edit(request, pk):
    afp = get_object_or_404(AFP, pk=pk)
    if request.method == 'POST':
        form = AFPForm(request.POST, instance=afp)
        if form.is_valid():
            form.save()
            messages.success(request, 'AFP actualizada correctamente')
            return redirect('nomina:afp_list')
    else:
        form = AFPForm(instance=afp)
    return render(request, 'nomina/afp_form.html', {
        'form': form,
        'accion': 'Editar',
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def afp_toggle(request, pk):
    afp = get_object_or_404(AFP, pk=pk)
    afp.activo = not afp.activo
    afp.save()
    estado = 'activada' if afp.activo else 'desactivada'
    messages.success(request, f"AFP '{afp.nombre}' {estado}.")
    return redirect('nomina:afp_list')


# ==========================================
# ARS
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ars_list(request):
    ars_objs = ARS.objects.all().order_by('nombre')
    return render(request, 'nomina/ars_list.html', {'ars_list': ars_objs})


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ars_create(request):
    if request.method == 'POST':
        form = ARSForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ARS creada correctamente')
            return redirect('nomina:ars_list')
    else:
        form = ARSForm()
    return render(request, 'nomina/ars_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ars_edit(request, pk):
    ars = get_object_or_404(ARS, pk=pk)
    if request.method == 'POST':
        form = ARSForm(request.POST, instance=ars)
        if form.is_valid():
            form.save()
            messages.success(request, 'ARS actualizada correctamente')
            return redirect('nomina:ars_list')
    else:
        form = ARSForm(instance=ars)
    return render(request, 'nomina/ars_form.html', {
        'form': form,
        'accion': 'Editar',
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ars_toggle(request, pk):
    ars = get_object_or_404(ARS, pk=pk)
    ars.activo = not ars.activo
    ars.save()
    estado = 'activada' if ars.activo else 'desactivada'
    messages.success(request, f"ARS '{ars.nombre}' {estado}.")
    return redirect('nomina:ars_list')


# ==========================================
# TIPOS DE INGRESO
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_ingreso_list(request):
    tipos = TipoIngreso.objects.all().order_by('nombre')
    return render(request, 'nomina/tipo_ingreso_list.html', {'tipos': tipos})


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_ingreso_create(request):
    if request.method == 'POST':
        form = TipoIngresoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de ingreso creado correctamente')
            return redirect('nomina:tipo_ingreso_list')
    else:
        form = TipoIngresoForm()
    return render(request, 'nomina/tipo_ingreso_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_ingreso_toggle(request, pk):
    tipo = get_object_or_404(TipoIngreso, pk=pk)
    tipo.activo = not tipo.activo
    tipo.save()
    estado = 'activado' if tipo.activo else 'desactivado'
    messages.success(request, f"'{tipo.nombre}' {estado}.")
    return redirect('nomina:tipo_ingreso_list')


# ==========================================
# TIPOS DE DESCUENTO
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_descuento_list(request):
    tipos = TipoDescuento.objects.all().order_by('nombre')
    return render(request, 'nomina/tipo_descuento_list.html', {'tipos': tipos})


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_descuento_create(request):
    if request.method == 'POST':
        form = TipoDescuentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de descuento creado correctamente')
            return redirect('nomina:tipo_descuento_list')
    else:
        form = TipoDescuentoForm()
    return render(request, 'nomina/tipo_descuento_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def tipo_descuento_toggle(request, pk):
    tipo = get_object_or_404(TipoDescuento, pk=pk)
    tipo.activo = not tipo.activo
    tipo.save()
    estado = 'activado' if tipo.activo else 'desactivado'
    messages.success(request, f"'{tipo.nombre}' {estado}.")
    return redirect('nomina:tipo_descuento_list')


# ==========================================
# CONFIGURACION NOMINA (EMPLEADOS)
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def configuracion_nomina_list(request):
    centro = request.centro

    empleados = ConfiguracionNomina.objects.filter(
        centro=centro
    ).select_related(
        'usuario', 'cargo', 'afp', 'ars'
    )

    q = request.GET.get('q', '').strip()
    if q:
        empleados = empleados.filter(
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(usuario__username__icontains=q) |
            Q(cargo__nombre__icontains=q)
        )

    empleados = empleados.order_by('usuario__first_name')

    activos = empleados.filter(activo_nomina=True).count()

    return render(request, 'nomina/configuracion_nomina_list.html', {
        'empleados': empleados,
        'activos': activos,
        'q': q,
    })


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def configuracion_nomina_create(request):
    centro = request.centro

    if request.method == 'POST':
        form = ConfiguracionNominaForm(
            request.POST,
            centro_id=centro.id,
        )
        if form.is_valid():
            configuracion = form.save(commit=False)
            configuracion.centro = centro
            configuracion.save()
            messages.success(
                request,
                'Configuración de nómina creada correctamente'
            )
            return redirect('nomina:configuracion_nomina_list')
    else:
        form = ConfiguracionNominaForm(centro_id=centro.id)

    return render(request, 'nomina/configuracion_nomina_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def configuracion_nomina_edit(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )

    if request.method == 'POST':
        form = ConfiguracionNominaForm(
            request.POST,
            instance=configuracion,
            centro_id=centro.id,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Configuración actualizada correctamente'
            )
            return redirect('nomina:configuracion_nomina_list')
    else:
        form = ConfiguracionNominaForm(
            instance=configuracion,
            centro_id=centro.id,
        )

    return render(request, 'nomina/configuracion_nomina_form.html', {
        'form': form,
        'accion': 'Editar',
        'configuracion': configuracion,
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def configuracion_nomina_toggle(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )
    configuracion.activo_nomina = not configuracion.activo_nomina
    configuracion.save()

    estado = 'activado' if configuracion.activo_nomina else 'desactivado'
    messages.success(
        request,
        f"Empleado {configuracion.usuario.get_full_name()} {estado} para nómina."
    )
    return redirect('nomina:configuracion_nomina_list')


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def configuracion_nomina_delete(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )

    if configuracion.nominas.exists():
        messages.error(
            request,
            "No se puede eliminar: el empleado ya tiene nóminas generadas. "
            "Desactívalo para nómina si es necesario."
        )
        return redirect('nomina:configuracion_nomina_list')

    nombre = configuracion.usuario.get_full_name()
    configuracion.delete()
    messages.success(request, f"Configuración de {nombre} eliminada.")

    return redirect('nomina:configuracion_nomina_list')


# ==========================================
# EMPLEADO DETALLE (ingresos/descuentos fijos)
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def empleado_detalle(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina.objects.select_related(
            'usuario', 'cargo', 'afp', 'ars'
        ),
        pk=pk,
        centro=centro,
    )

    ingresos = configuracion.ingresos_fijos.filter(activo=True)
    descuentos = configuracion.descuentos_fijos.filter(activo=True)

    return render(request, 'nomina/empleado_detalle.html', {
        'configuracion': configuracion,
        'ingresos': ingresos,
        'descuentos': descuentos,
        'form_ingreso': IngresoEmpleadoForm(),
        'form_descuento': DescuentoEmpleadoForm(),
    })


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ingreso_empleado_create(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )

    form = IngresoEmpleadoForm(request.POST)
    if form.is_valid():
        ingreso = form.save(commit=False)
        ingreso.configuracion = configuracion
        ingreso.save()
        messages.success(request, 'Ingreso fijo agregado correctamente.')
    else:
        messages.error(request, 'No se pudo agregar el ingreso.')

    return redirect('nomina:empleado_detalle', pk=pk)


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def ingreso_empleado_delete(request, pk, ingreso_id):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )
    ingreso = get_object_or_404(
        IngresoEmpleado,
        pk=ingreso_id,
        configuracion=configuracion,
    )
    ingreso.delete()
    messages.success(request, 'Ingreso fijo eliminado.')
    return redirect('nomina:empleado_detalle', pk=pk)


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def descuento_empleado_create(request, pk):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )

    form = DescuentoEmpleadoForm(request.POST)
    if form.is_valid():
        descuento = form.save(commit=False)
        descuento.configuracion = configuracion
        descuento.save()
        messages.success(request, 'Descuento fijo agregado correctamente.')
    else:
        messages.error(request, 'No se pudo agregar el descuento.')

    return redirect('nomina:empleado_detalle', pk=pk)


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def descuento_empleado_delete(request, pk, descuento_id):
    centro = request.centro
    configuracion = get_object_or_404(
        ConfiguracionNomina,
        pk=pk,
        centro=centro,
    )
    descuento = get_object_or_404(
        DescuentoEmpleado,
        pk=descuento_id,
        configuracion=configuracion,
    )
    descuento.delete()
    messages.success(request, 'Descuento fijo eliminado.')
    return redirect('nomina:empleado_detalle', pk=pk)


# ==========================================
# PERIODOS NOMINA
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def periodo_nomina_list(request):
    centro = request.centro

    generar_periodos_si_no_existen(centro.id)

    periodos = PeriodoNomina.objects.filter(centro=centro)

    anio = request.GET.get('anio', '')
    if anio:
        periodos = periodos.filter(anio=anio)

    periodos = periodos.annotate(
        total_neto=Sum(
            'nominas__neto_pagar',
            filter=Q(nominas__estado__in=ESTADOS_ACTIVOS),
        ),
        cantidad_empleados=Count(
            'nominas',
            filter=Q(nominas__estado__in=ESTADOS_ACTIVOS),
        ),
    ).order_by('-anio', '-mes', '-numero_periodo')

    anios_disponibles = (
        PeriodoNomina.objects.filter(centro=centro)
        .values_list('anio', flat=True)
        .distinct()
        .order_by('-anio')
    )

    return render(request, 'nomina/periodo_nomina_list.html', {
        'periodos': periodos,
        'anios_disponibles': anios_disponibles,
        'anio_seleccionado': anio,
        'meses': MESES,
    })


# ==========================================
# GENERAR NOMINA (AJAX)
# ==========================================

@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
@ratelimit(key='ip', rate='100/h', method='POST', block=True)
def generar_nomina_view(request, periodo_id):
    centro = request.centro

    periodo = get_object_or_404(
        PeriodoNomina,
        id=periodo_id,
        centro=centro,
    )

    if periodo.nomina_generada:
        return JsonResponse({
            'success': False,
            'message': 'La nómina ya fue generada'
        })

    if periodo.cerrado:
        return JsonResponse({
            'success': False,
            'message': 'Este período está cerrado'
        })

    try:
        with transaction.atomic():
            generar_nomina(
                periodo=periodo,
                centro_id=centro.id,
                generado_por=request.user,
            )

        try:
            resultado = enviar_notificaciones_nomina(periodo)
        except Exception:
            logger.exception(
                'Error enviando notificaciones de nómina del período %s',
                periodo_id,
            )
            resultado = {'enviados': 0, 'sin_correo': 0, 'errores': 0}

        mensaje = 'Nómina generada correctamente'
        if resultado['enviados']:
            mensaje += (
                f" Se enviaron {resultado['enviados']} correos con su recibo."
            )
        if resultado['sin_correo']:
            mensaje += (
                f" {resultado['sin_correo']} empleados sin correo registrado."
            )
        if resultado['errores']:
            mensaje += (
                f" {resultado['errores']} correos no se pudieron enviar."
            )

        return JsonResponse({
            'success': True,
            'message': mensaje,
        })

    except Exception as e:
        logger.exception('Error generando nómina para periodo %s', periodo_id)
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


# ==========================================
# DETALLE PERIODO
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def periodo_detalle(request, periodo_id):
    centro = request.centro

    periodo = get_object_or_404(
        PeriodoNomina.objects.select_related('centro'),
        id=periodo_id,
        centro=centro,
    )

    datos = datos_periodo_detalle(periodo)

    return render(request, 'nomina/periodo_detalle.html', {
        'periodo': periodo,
        'nominas': datos['nominas'],
        'totales': datos['totales'],
        'meses': MESES,
        'datos_impresion': datos['datos_impresion'],
    })


# ==========================================
# CERRAR / ANULAR PERIODO
# ==========================================

@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def periodo_cerrar(request, periodo_id):
    centro = request.centro
    periodo = get_object_or_404(
        PeriodoNomina,
        id=periodo_id,
        centro=centro,
    )

    if not periodo.nomina_generada:
        messages.error(request, 'Debes generar la nómina antes de cerrar.')
        return redirect('nomina:periodo_detalle', periodo_id=periodo_id)

    periodo.cerrado = True
    periodo.save()
    messages.success(request, 'Período cerrado. Ya no permite modificaciones.')
    return redirect('nomina:periodo_detalle', periodo_id=periodo_id)


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def periodo_anular(request, periodo_id):
    centro = request.centro
    periodo = get_object_or_404(
        PeriodoNomina,
        id=periodo_id,
        centro=centro,
    )

    try:
        anular_nomina(periodo)
        messages.success(
            request,
            'Nómina anulada. El período quedó listo para regenerar.'
        )
    except Exception as e:
        messages.error(request, str(e))

    return redirect('nomina:periodo_detalle', periodo_id=periodo_id)


# ==========================================
# ESTADO DE NOMINA INDIVIDUAL
# ==========================================

TRANSICIONES = {
    'revisar': ('REVISADA', 'REVISADA'),
    'aprobar': ('APROBADA', 'APROBADA'),
    'pagar': ('PAGADA', 'PAGADA'),
}


@require_POST
@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def nomina_estado(request, nomina_id):
    centro = request.centro
    nomina = get_object_or_404(
        Nomina,
        id=nomina_id,
        periodo__centro=centro,
    )

    if nomina.periodo.cerrado:
        messages.error(request, 'El período está cerrado.')
        return redirect('nomina:periodo_detalle', periodo_id=nomina.periodo_id)

    accion = request.POST.get('accion', '')
    estado, _ = TRANSICIONES.get(accion, (None, None))

    if estado is None:
        messages.error(request, 'Acción inválida.')
        return redirect('nomina:periodo_detalle', periodo_id=nomina.periodo_id)

    if nomina.estado in ('PAGADA', 'ANULADA'):
        messages.error(
            request,
            'No se puede modificar una nómina pagada o anulada.'
        )
        return redirect('nomina:periodo_detalle', periodo_id=nomina.periodo_id)

    nomina.estado = estado
    if accion == 'pagar':
        nomina.pagado = True
        nomina.fecha_pago = timezone.localdate()
    nomina.save()

    messages.success(request, f"Nómina marcada como {ESTADO_LABELS[estado]}.")
    return redirect('nomina:periodo_detalle', periodo_id=nomina.periodo_id)


# ==========================================
# BOLETA DE PAGO
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def boleta_pago(request, nomina_id):
    centro = request.centro
    nomina = get_object_or_404(
        Nomina.objects.select_related(
            'periodo__centro',
            'usuario',
            'configuracion__cargo',
        ),
        id=nomina_id,
        periodo__centro=centro,
    )

    datos = datos_boleta_pago(nomina)

    return render(request, 'nomina/boleta_pago.html', {
        'nomina': nomina,
        'ingresos': datos['ingresos'],
        'descuentos': datos['descuentos'],
    })


# ==========================================
# HISTORIAL NOMINA
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def historial_nomina(request):
    centro = request.centro

    historial = historial_nomina_cached(centro)

    return render(request, 'nomina/historial_nomina.html', {
        'historial': historial,
    })


# ==========================================
# DETALLE NOMINA (AJAX)
# ==========================================

@login_required
@centro_required
@role_required(*ROLES_NOMINA)
def detalle_nomina_view(request, periodo_id):
    centro = request.centro
    periodo = get_object_or_404(
        PeriodoNomina,
        id=periodo_id,
        centro=centro,
    )

    nominas = (
        periodo.nominas.all()
        .select_related('configuracion__cargo', 'usuario')
        .exclude(estado='ANULADA')
    )

    data = []
    total_general = 0

    for nomina in nominas:
        empleado = nomina.usuario.get_full_name()
        data.append({
            'empleado': empleado,
            'salario': float(nomina.salario_base),
            'ingresos': float(nomina.total_ingresos),
            'descuentos': float(nomina.total_descuentos),
            'neto': float(nomina.neto_pagar),
            'estado': nomina.estado,
        })
        total_general += nomina.neto_pagar

    return JsonResponse({
        'success': True,
        'periodo': periodo.descripcion,
        'empleados': data,
        'total_general': float(total_general),
    })
