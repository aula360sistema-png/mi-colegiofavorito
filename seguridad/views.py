from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import role_required
from core.utils.session import get_centro_activo

from .forms import ConsentimientoInformadoForm
from .models import ConsentimientoInformado, RegistroAccesoDato, RegistroRetencion
from .utils import (
    anonimizar_estudiante,
    anonimizar_historial_clinico,
    estudiantes_anonimizables,
)


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def consentimiento_list(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')
    items = ConsentimientoInformado.objects.filter(
        centro=centro,
    ).select_related('estudiante', 'anio_escolar')
    return render(request, 'seguridad/consentimiento_list.html', {'items': items})


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def consentimiento_create(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')
    from core.utils.anio import obtener_anio_activo
    anio = obtener_anio_activo(centro)

    if request.method == 'POST':
        form = ConsentimientoInformadoForm(request.POST)
        if form.is_valid():
            consent = form.save(commit=False)
            consent.centro = centro
            consent.anio_escolar = anio
            consent.ip_firma = request.META.get('REMOTE_ADDR')
            consent.user_agent_firma = request.META.get('HTTP_USER_AGENT', '')
            consent.save()
            RegistroAccesoDato.objects.create(
                usuario=request.user,
                tipo_dato='datos_personales',
                accion='escritura',
                descripcion=f'Consentimiento informado firmado para {consent.estudiante}',
                estudiante=consent.estudiante,
                ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            messages.success(request, 'Consentimiento informado registrado exitosamente.')
            return redirect('seguridad:consentimiento_list')
    else:
        form = ConsentimientoInformadoForm()
    return render(request, 'seguridad/consentimiento_form.html', {'form': form})


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def consentimiento_detail(request, pk):
    consent = get_object_or_404(
        ConsentimientoInformado.objects.select_related('estudiante', 'centro', 'anio_escolar'),
        pk=pk,
    )
    RegistroAccesoDato.objects.create(
        usuario=request.user,
        tipo_dato='datos_personales',
        accion='lectura',
        descripcion=f'Consulta de consentimiento #{consent.pk}',
        estudiante=consent.estudiante,
        ip=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    return render(request, 'seguridad/consentimiento_detail.html', {'obj': consent})


@login_required
@role_required('director', 'admin', 'superadmin')
def consentimiento_revocar(request, pk):
    consent = get_object_or_404(ConsentimientoInformado, pk=pk)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        consent.revocar(motivo=motivo)
        RegistroAccesoDato.objects.create(
            usuario=request.user,
            tipo_dato='datos_personales',
            accion='escritura',
            descripcion=f'Consentimiento #{consent.pk} revocado. Motivo: {motivo}',
            estudiante=consent.estudiante,
            ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        messages.warning(request, 'Consentimiento revocado.')
        return redirect('seguridad:consentimiento_list')
    return render(request, 'seguridad/consentimiento_revocar.html', {'obj': consent})


@login_required
@role_required('director', 'admin', 'superadmin')
def registros_acceso(request):
    items = RegistroAccesoDato.objects.select_related(
        'usuario', 'estudiante'
    )[:200]
    return render(request, 'seguridad/registros_acceso.html', {'items': items})


@login_required
@role_required('director', 'admin', 'superadmin')
def anonymize_students(request):
    if request.method != 'POST':
        return redirect('seguridad:dashboard')
    candidatos = estudiantes_anonimizables()
    count = 0
    for est in candidatos:
        campos = anonimizar_estudiante(est)
        hc = getattr(est, 'historial_clinico', None)
        if hc:
            anonimizar_historial_clinico(hc)
        RegistroAccesoDato.objects.create(
            usuario=request.user,
            tipo_dato='datos_personales',
            accion='anonimizacion',
            descripcion=f'Datos anonimizados: {campos}',
            estudiante=est,
            ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        count += 1
    RegistroRetencion.objects.create(
        tipo_dato='datos_personales',
        accion='anonimizacion',
        registros_afectados=count,
        detalle={'estudiantes_anonimizados': count},
        ejecutado_por=request.user,
    )
    messages.success(request, f'{count} estudiante(s) anonimizado(s) correctamente.')
    return redirect('seguridad:dashboard')


@login_required
@role_required('admin', 'superadmin')
def dashboard(request):
    total_consentimientos = ConsentimientoInformado.objects.count()
    consentimientos_activos = ConsentimientoInformado.objects.filter(activo=True).count()
    consentimientos_revocados = total_consentimientos - consentimientos_activos
    total_accesos = RegistroAccesoDato.objects.count()
    accesos_hoy = RegistroAccesoDato.objects.filter(
        fecha__date=__import__('django.utils.timezone', fromlist=['now']).now().date()
    ).count()
    total_retenciones = RegistroRetencion.objects.count()

    return render(request, 'seguridad/dashboard.html', {
        'total_consentimientos': total_consentimientos,
        'consentimientos_activos': consentimientos_activos,
        'consentimientos_revocados': consentimientos_revocados,
        'total_accesos': total_accesos,
        'accesos_hoy': accesos_hoy,
        'total_retenciones': total_retenciones,
    })
