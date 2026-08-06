import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from core.decorators import role_required

from nomina.services import (
    generar_nomina,
    generar_periodos_si_no_existen,
)

from .models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    Nomina,
    PeriodoNomina,
)

from .forms import (
    AFPForm,
    ARSForm,
    CargoForm,
    ConfiguracionNominaForm,
)

logger = logging.getLogger(__name__)


# ==========================================
# CARGOS
# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def cargo_list(request):

    cargos = Cargo.objects.filter(
        activo=True
    ).order_by('nombre')

    return render(
        request,
        'nomina/cargo_list.html',
        {
            'cargos': cargos
        }
    )

# ==========================================
# AFP
# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def afp_list(request):

    afps = AFP.objects.filter(
        activo=True
    ).order_by('nombre')

    return render(
        request,
        'nomina/afp_list.html',
        {
            'afps': afps
        }
    )


@login_required
@role_required('director', 'admin', 'superadmin')
def afp_create(request):

    if request.method == 'POST':

        form = AFPForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'AFP creada correctamente'
            )

            return redirect('nomina:afp_list')

    else:

        form = AFPForm()

    return render(
        request,
        'nomina/afp_form.html',
        {
            'form': form,
            'accion': 'Crear'
        }
    )


# ==========================================
# ARS
# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def ars_list(request):

    ars_list = ARS.objects.filter(
        activo=True
    ).order_by('nombre')

    return render(
        request,
        'nomina/ars_list.html',
        {
            'ars_list': ars_list
        }
    )


@login_required
@role_required('director', 'admin', 'superadmin')
def ars_create(request):

    if request.method == 'POST':

        form = ARSForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'ARS creada correctamente'
            )

            return redirect('nomina:ars_list')

    else:

        form = ARSForm()

    return render(
        request,
        'nomina/ars_form.html',
        {
            'form': form,
            'accion': 'Crear'
        }
    )


@login_required
@role_required('director', 'admin', 'superadmin')
def cargo_create(request):

    if request.method == 'POST':

        form = CargoForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Cargo creado correctamente'
            )

            return redirect('nomina:cargo_list')

    else:

        form = CargoForm()

    return render(
        request,
        'nomina/cargo_form.html',
        {
            'form': form,
            'accion': 'Crear'
        }
    )


# ==========================================
# CONFIGURACION NOMINA
# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def configuracion_nomina_list(request):

    centro_id = request.session.get('centro_id')

    empleados = ConfiguracionNomina.objects.filter(
        centro_id=centro_id
    ).select_related(
        'usuario',
        'cargo',
        'afp',
        'ars'
    ).order_by(
        'usuario__first_name'
    )

    return render(
        request,
        'nomina/configuracion_nomina_list.html',
        {
            'empleados': empleados
        }
    )


@login_required
@role_required('director', 'admin', 'superadmin')
def configuracion_nomina_create(request):

    centro_id = request.session.get('centro_id')

    if request.method == 'POST':

        form = ConfiguracionNominaForm(
            request.POST,
            centro_id=centro_id
        )

        if form.is_valid():

            configuracion = form.save(commit=False)

            configuracion.centro_id = centro_id

            configuracion.save()

            messages.success(
                request,
                'Configuración de nómina creada correctamente'
            )

            return redirect(
                'nomina:configuracion_nomina_list'
            )

    else:

        form = ConfiguracionNominaForm(
            centro_id=centro_id
        )

    return render(
        request,
        'nomina/configuracion_nomina_form.html',
        {
            'form': form,
            'accion': 'Crear'
        }
    )


# ==========================================
# PERIODOS NOMINA
# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def periodo_nomina_list(request):

    centro_id = request.session.get('centro_id')

    # ======================================
    # GENERAR PERIODOS AUTOMATICOS
    # ======================================

    generar_periodos_si_no_existen(
        centro_id
    )

    periodos = PeriodoNomina.objects.filter(
        centro_id=centro_id
    ).order_by(
        '-anio',
        '-mes',
        '-numero_periodo'
    )

    return render(
        request,
        'nomina/periodo_nomina_list.html',
        {
            'periodos': periodos
        }
    )


# ==========================================
# GENERAR NOMINA ERP
# ==========================================

@require_POST
@login_required
@role_required('director', 'admin', 'superadmin')
def generar_nomina_view(request, periodo_id):

    centro_id = request.session.get('centro_id')

    try:

        periodo = PeriodoNomina.objects.get(
            id=periodo_id,
            centro_id=centro_id
        )

    except PeriodoNomina.DoesNotExist:

        return JsonResponse({
            'success': False,
            'message': 'Período no válido'
        })

    # ======================================
    # VALIDACIONES
    # ======================================

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
                centro_id=centro_id
            )

            periodo.nomina_generada = True
            periodo.save()

        return JsonResponse({
            'success': True,
            'message': 'Nómina generada correctamente'
        })

    except Exception as e:

        logger.exception('Error generando nómina para periodo %s', periodo_id)

        return JsonResponse({
            'success': False,
            'message': str(e)
        })


# ==========================================

# HISTORIAL NOMINA

# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def historial_nomina(request):

    centro_id = request.session.get('centro_id')

    MESES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}

    periodos = PeriodoNomina.objects.filter(
        centro_id=centro_id,
        nomina_generada=True
    ).order_by(
        '-anio',
        '-mes'
    )

    historial = {}

    for periodo in periodos:

        anio = periodo.anio

        mes = MESES.get(
            periodo.mes,
            str(periodo.mes)
        )

        if anio not in historial:
            historial[anio] = {}

        if mes not in historial[anio]:
            historial[anio][mes] = []

        historial[anio][mes].append(periodo)

    return render(
        request,
        'nomina/historial_nomina.html',
        {
            'historial': historial
        }
    )

# ==========================================

# DETALLE NOMINA AJAX

# ==========================================

@login_required
@role_required('director', 'admin', 'superadmin')
def detalle_nomina_view(request, periodo_id):


    centro_id = request.session.get('centro_id')

    periodo = get_object_or_404(
        PeriodoNomina,
        id=periodo_id,
        centro_id=centro_id
    )

    nominas = (
        Nomina.objects
        .filter(periodo=periodo)
       .select_related(
        'configuracion__cargo',
        'configuracion__afp',
        'configuracion__ars',
        'usuario'
         )
    )

    data = []

    total_general = 0

    for nomina in nominas:

        empleado = (
            nomina.configuracion.usuario.get_full_name()
            if nomina.configuracion and nomina.configuracion.usuario
            else 'Empleado'
        )

        data.append({
            'empleado': empleado,
            'salario': float(nomina.salario_base),
            'ingresos': float(nomina.total_ingresos),
            'descuentos': float(nomina.total_descuentos),
            'neto': float(nomina.neto_pagar),
        })

        total_general += nomina.neto_pagar

    return JsonResponse({
        'success': True,
        'periodo': periodo.descripcion,
        'empleados': data,
        'total_general': float(total_general)
    })

