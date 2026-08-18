import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string

from core.decorators import centro_required, role_required
from core.utils.session import get_centro_activo
from core.models import ConfiguracionCentro
from estudiantes.models import (
    Estudiante,
    HistorialClinicoEstudiante,
    Inscripcion,
    SolicitudCertificado,
)
from estudiantes.forms import SolicitudCertificadoTutorForm
from caja.services import tiene_deuda_pendiente
from usuarios.models import Usuario

from .forms import TutorForm
from .models import Tutor

logger = logging.getLogger(__name__)


@login_required
def tutor_inicio(request):
    if request.user.rol != 'tutor':
        return redirect('core:home')

    tutor = get_object_or_404(
        Tutor,
        usuario=request.user
    )

    from .services import datos_inicio_tutor
    from caja.services import deuda_detalle_estudiante

    lista = datos_inicio_tutor(tutor)

    estudiantes = []
    deuda_total = {
        'saldo_total': 0,
        'vencida': 0,
        'proxima': 0,
        'tiene_deuda': False,
    }
    for item in lista:
        deuda = deuda_detalle_estudiante(tutor.centro, item['estudiante'])
        deuda_total['saldo_total'] += deuda['saldo_total']
        deuda_total['vencida'] += deuda['vencida']
        deuda_total['proxima'] += deuda['proxima']
        estudiantes.append({**item, 'deuda': deuda})

    deuda_total['tiene_deuda'] = deuda_total['saldo_total'] > 0

    return render(request, 'tutores/tutor_inicio.html', {
        'tutor': tutor,
        'estudiantes': estudiantes,
        'deuda_total': deuda_total,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def tutor_list(request):
    centro = request.centro

    q = request.GET.get('q', '').strip()

    from .services import tutores_del_centro

    tutores = tutores_del_centro(centro)

    if q:
        tutores = [
            t for t in tutores
            if q.lower() in t.primer_nombre.lower()
            or q.lower() in (t.segundo_nombre or '').lower()
            or q.lower() in t.primer_apellido.lower()
            or q.lower() in (t.segundo_apellido or '').lower()
            or q.lower() in t.cedula.lower()
        ]

    paginator = Paginator(tutores, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'tutores/tutor_list.html', {
        'centro': centro,
        'tutores': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'total': paginator.count,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def tutor_create(request):
    centro = request.centro

    if request.method == 'POST':
        form = TutorForm(request.POST, request.FILES, centro=centro)

        if form.is_valid():
            tutor = form.save(commit=False)
            tutor.centro = centro

            password = get_random_string(8)

            usuario = Usuario.objects.create_user(
                username=tutor.cedula,
                email=tutor.correo_personal or f"{tutor.cedula}@colegio.com",
                password=password
            )
            usuario.rol = 'tutor'
            usuario.debe_cambiar_password = True
            usuario.save()

            tutor.usuario = usuario
            tutor.save()
            form.save_m2m()

            return render(
                request,
                'usuarios/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password,
                    'centro': centro.nombre,
                    'tipo_nombre': 'Tutor',
                    'tipo_slug': 'tutor',
                }
            )
    else:
        form = TutorForm(centro=centro)

    return render(request, 'tutores/tutor_form.html', {
        'form': form,
        'tutor': None,
        'accion': 'Crear',
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def tutor_update(request, pk):
    centro = request.centro

    tutor = get_object_or_404(
        Tutor,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = TutorForm(request.POST, request.FILES, instance=tutor, centro=centro)

        if form.is_valid():
            form.save()
            messages.success(request, 'Tutor actualizado correctamente.')
            return redirect('tutores:tutor_detail', pk=tutor.pk)
    else:
        form = TutorForm(instance=tutor, centro=centro)

    return render(request, 'tutores/tutor_form.html', {
        'form': form,
        'tutor': tutor,
        'accion': 'Editar',
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def tutor_detail(request, pk):
    centro = request.centro

    tutor = get_object_or_404(
        Tutor,
        pk=pk,
        centro=centro
    )

    estudiantes = tutor.estudiantes.select_related('centro').order_by(
        'primer_apellido', 'primer_nombre'
    )

    return render(request, 'tutores/tutor_detail.html', {
        'tutor': tutor,
        'estudiantes': estudiantes,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def tutor_delete(request, pk):
    centro = request.centro

    tutor = get_object_or_404(
        Tutor,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        if tutor.usuario:
            tutor.usuario.delete()
        tutor.delete()
        messages.success(request, 'Tutor eliminado correctamente.')
        return redirect('tutores:tutor_list')

    return render(request, 'tutores/tutor_confirm_delete.html', {
        'tutor': tutor,
    })


@login_required
def tutor_estudiante_detalle(request, estudiante_id):
    if request.user.rol != 'tutor':
        return redirect('core:home')

    tutor = get_object_or_404(
        Tutor,
        usuario=request.user
    )

    estudiante = get_object_or_404(
        tutor.estudiantes,
        pk=estudiante_id
    )

    from estudiantes.services.kardex import construir_kardex

    kardex = construir_kardex(estudiante, estudiante.centro)

    anio_actual = None
    inscripcion_actual = None

    for y in kardex['anios']:
        if y['anio'].activo:
            inscripcion_actual = y
            break

    if inscripcion_actual is None and kardex['anios']:
        inscripcion_actual = kardex['anios'][-1]

    if inscripcion_actual:
        anio_actual = inscripcion_actual['anio']

    return render(request, 'tutores/tutor_estudiante_detalle.html', {
        'tutor': tutor,
        'estudiante': estudiante,
        'kardex': kardex,
        'inscripcion_actual': inscripcion_actual,
        'anio_actual': anio_actual,
        'total_anios': len(kardex['anios']),
    })


@login_required
def tutor_solicitudes(request):
    if request.user.rol != 'tutor':
        return redirect('core:home')

    tutor = get_object_or_404(
        Tutor,
        usuario=request.user
    )

    estudiantes = tutor.estudiantes.select_related('centro').order_by(
        'primer_apellido', 'primer_nombre'
    )

    solicitudes = (
        SolicitudCertificado.objects
        .filter(estudiante__in=estudiantes)
        .select_related('estudiante', 'solicitante')
        .order_by('-created_at')
    )

    config = ConfiguracionCentro.objects.filter(
        centro=tutor.centro
    ).first()

    if request.method == 'POST':
        form = SolicitudCertificadoTutorForm(
            request.POST,
            estudiantes=estudiantes,
        )

        if form.is_valid():
            if config and not config.modulo_certificados:
                messages.error(
                    request,
                    'El centro no tiene habilitadas las solicitudes de certificados.'
                )
            elif tiene_deuda_pendiente(
                tutor.centro,
                form.cleaned_data['estudiante'],
            ):
                messages.error(
                    request,
                    (
                        f"No se puede solicitar el certificado: "
                        f"{form.cleaned_data['estudiante'].nombre_completo()} "
                        "tiene deuda pendiente."
                    )
                )
            else:
                solicitud = form.save(commit=False)
                solicitud.solicitante = request.user
                solicitud.monto = config.precio_certificado if config else 0
                solicitud.save()

                messages.success(
                    request,
                    (
                        f"Solicitud {solicitud.folio} registrada para "
                        f"{solicitud.estudiante.nombre_completo()}. "
                        f"Estado: {solicitud.get_estado_display()}."
                    )
                )
                return redirect('tutores:tutor_solicitudes')
    else:
        form = SolicitudCertificadoTutorForm(estudiantes=estudiantes)

    return render(
        request,
        'tutores/tutor_solicitudes.html',
        {
            'tutor': tutor,
            'estudiantes': estudiantes,
            'solicitudes': solicitudes,
            'form': form,
            'config': config,
            'modulo_activo': bool(config and config.modulo_certificados),
        }
    )


@login_required
def tutor_historial_clinico(request):
    if request.user.rol != 'tutor':
        return redirect('core:home')

    tutor = get_object_or_404(
        Tutor,
        usuario=request.user
    )

    estudiantes = tutor.estudiantes.select_related('centro').order_by(
        'primer_apellido', 'primer_nombre'
    )

    estudiante = None
    historial = None
    registros = HistorialClinicoEstudiante.objects.none()

    if estudiantes:
        estudiante_id = request.GET.get('estudiante')
        if estudiante_id:
            estudiante = get_object_or_404(
                estudiantes,
                pk=estudiante_id
            )
        else:
            estudiante = estudiantes.first()

    if estudiante:
        historial = getattr(estudiante, 'historial_clinico', None)
        registros = estudiante.registros_salud.order_by('-fecha')

    return render(
        request,
        'tutores/tutor_historial_clinico.html',
        {
            'tutor': tutor,
            'estudiantes': estudiantes,
            'estudiante': estudiante,
            'historial': historial,
            'registros': registros,
        }
    )
