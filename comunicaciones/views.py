from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import centro_required, role_required
from estudiantes.models import Estudiante
from tutores.models import Tutor

from .forms import CampaniaForm, ComunicadoForm
from .models import Campania, Comunicado
from .services import construir_destinatarios, procesar_campania

ROLES_COMUNICACIONES = ('director', 'secretaria', 'admin', 'superadmin')


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_list(request):
    centro = request.centro

    campanias = (
        Campania.objects
        .filter(centro=centro)
        .select_related('enviado_por')
        .prefetch_related('destinatarios')
        .order_by('-created_at')
    )

    paginator = Paginator(campanias, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'comunicaciones/campania_list.html', {
        'campanias': page_obj.object_list,
        'page_obj': page_obj,
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_create(request):
    centro = request.centro

    if request.method == 'POST':
        form = CampaniaForm(request.POST, centro=centro)

        if form.is_valid():
            campania = form.save(commit=False)
            campania.centro = centro
            campania.enviado_por = request.user
            campania.save()
            form.save_m2m()

            creados = construir_destinatarios(campania)

            messages.success(
                request,
                f'Campaña creada con {creados} destinatario(s) por generar '
                f'({campania.destinatarios.count()} en total).'
            )
            return redirect('comunicaciones:campania_detail', pk=campania.pk)
    else:
        initial = {}
        tutor_id = request.GET.get('tutor')

        if tutor_id:
            tutor = get_object_or_404(
                Tutor,
                pk=tutor_id,
                centro=centro,
            )
            initial = {
                'alcance': 'seleccion',
                'tutores': [tutor.pk],
            }

        form = CampaniaForm(centro=centro, initial=initial)

    return render(request, 'comunicaciones/campania_form.html', {
        'form': form,
        'accion': 'Crear',
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_update(request, pk):
    centro = request.centro

    campania = get_object_or_404(
        Campania,
        pk=pk,
        centro=centro,
    )

    if campania.estado != 'borrador':
        messages.warning(
            request,
            'Solo se puede editar una campaña que esté en borrador.'
        )
        return redirect('comunicaciones:campania_detail', pk=campania.pk)

    if request.method == 'POST':
        form = CampaniaForm(request.POST, instance=campania, centro=centro)

        if form.is_valid():
            campania = form.save()

            campania.destinatarios.all().delete()
            creados = construir_destinatarios(campania)

            messages.success(
                request,
                f'Campaña actualizada con {creados} destinatario(s).'
            )
            return redirect('comunicaciones:campania_detail', pk=campania.pk)
    else:
        form = CampaniaForm(instance=campania, centro=centro)

    return render(request, 'comunicaciones/campania_form.html', {
        'form': form,
        'campania': campania,
        'accion': 'Editar',
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_detail(request, pk):
    centro = request.centro

    campania = get_object_or_404(
        Campania,
        pk=pk,
        centro=centro,
    )

    destinatarios = campania.destinatarios.select_related('tutor').order_by(
        'tutor__primer_apellido', 'tutor__primer_nombre', 'canal'
    )

    return render(request, 'comunicaciones/campania_detail.html', {
        'campania': campania,
        'destinatarios': destinatarios,
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_enviar(request, pk):
    centro = request.centro

    campania = get_object_or_404(
        Campania,
        pk=pk,
        centro=centro,
    )

    if request.method == 'POST':
        procesar_campania(campania)

        exitosos = campania.destinatarios.filter(estado='enviado').count()
        fallidos = campania.destinatarios.filter(estado='fallido').count()
        sin_contacto = campania.destinatarios.filter(
            estado='sin_contacto'
        ).count()

        messages.success(
            request,
            f'Envío procesado: {exitosos} enviado(s), '
            f'{fallidos} fallido(s), {sin_contacto} sin contacto.'
        )
        return redirect('comunicaciones:campania_detail', pk=campania.pk)

    return redirect('comunicaciones:campania_detail', pk=campania.pk)


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def campania_delete(request, pk):
    centro = request.centro

    campania = get_object_or_404(
        Campania,
        pk=pk,
        centro=centro,
    )

    if request.method == 'POST':
        campania.delete()
        messages.success(request, 'Campaña eliminada correctamente.')
        return redirect('comunicaciones:campania_list')

    return render(request, 'comunicaciones/campania_confirm_delete.html', {
        'campania': campania,
    })

# =========================
# COMUNICADOS / ANUNCIOS POR SECCION
# =========================

@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def comunicado_list(request):
    centro = request.centro

    comunicados = (
        Comunicado.objects
        .filter(centro=centro)
        .select_related('seccion', 'autor')
    )

    q = request.GET.get('q', '').strip()
    if q:
        comunicados = comunicados.filter(titulo__icontains=q)

    seccion_id = request.GET.get('seccion', '').strip()
    if seccion_id:
        comunicados = comunicados.filter(seccion_id=seccion_id)

    estado = request.GET.get('estado', '').strip()
    hoy = timezone.localdate()
    if estado == 'vigente':
        comunicados = comunicados.filter(
            Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=hoy),
            fecha_publicacion__date__lte=hoy,
        )
    elif estado == 'vencido':
        comunicados = comunicados.filter(fecha_vencimiento__lt=hoy)

    from academico.models import Seccion

    secciones = Seccion.objects.filter(centro=centro).order_by('nombre')

    paginator = Paginator(comunicados, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'comunicaciones/comunicado_list.html', {
        'comunicados': page_obj.object_list,
        'page_obj': page_obj,
        'secciones': secciones,
        'q': q,
        'seccion_sel': seccion_id,
        'estado': estado,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def comunicado_create(request):
    centro = request.centro

    if request.method == 'POST':
        form = ComunicadoForm(request.POST, centro=centro)

        if form.is_valid():
            comunicado = form.save(commit=False)
            comunicado.centro = centro
            comunicado.autor = request.user
            comunicado.save()

            messages.success(request, 'Comunicado publicado correctamente.')
            return redirect('comunicaciones:comunicado_list')
    else:
        form = ComunicadoForm(centro=centro, initial={
            'fecha_publicacion': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        })

    return render(request, 'comunicaciones/comunicado_form.html', {
        'form': form,
        'accion': 'Publicar',
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def comunicado_update(request, pk):
    centro = request.centro

    comunicado = get_object_or_404(Comunicado, pk=pk, centro=centro)

    if request.method == 'POST':
        form = ComunicadoForm(request.POST, instance=comunicado, centro=centro)

        if form.is_valid():
            comunicado = form.save(commit=False)
            comunicado.autor = request.user
            comunicado.save()

            messages.success(request, 'Comunicado actualizado.')
            return redirect('comunicaciones:comunicado_list')
    else:
        inicial = {}
        if comunicado.fecha_publicacion:
            inicial['fecha_publicacion'] = timezone.localtime(
                comunicado.fecha_publicacion
            ).strftime('%Y-%m-%dT%H:%M')
        form = ComunicadoForm(
            instance=comunicado, centro=centro, initial=inicial)

    return render(request, 'comunicaciones/comunicado_form.html', {
        'form': form,
        'comunicado': comunicado,
        'accion': 'Editar',
        'centro': centro,
    })


@login_required
@centro_required
@role_required(*ROLES_COMUNICACIONES)
def comunicado_delete(request, pk):
    centro = request.centro

    comunicado = get_object_or_404(Comunicado, pk=pk, centro=centro)

    if request.method == 'POST':
        comunicado.delete()
        messages.success(request, 'Comunicado eliminado correctamente.')
        return redirect('comunicaciones:comunicado_list')

    return render(request, 'comunicaciones/comunicado_confirm_delete.html', {
        'comunicado': comunicado,
    })


# ---------------------------------------------------------------------------
# PORTALES (estudiante y tutor): solo lectura
# ---------------------------------------------------------------------------

def _portal_comunicados(request, lista, titulo):
    """Render compartido del listado del portal."""
    hoy = timezone.localdate()
    visibles = [c for c in lista if c.esta_vigente(hoy)]

    paginator = Paginator(visibles, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'comunicaciones/comunicados_portal.html', {
        'comunicados': page_obj.object_list,
        'page_obj': page_obj,
        'titulo': titulo,
    })


@login_required
def estudiante_comunicados(request):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(Estudiante, usuario=request.user)

    from .services.comunicados import comunicados_para_estudiante

    return _portal_comunicados(
        request,
        comunicados_para_estudiante(estudiante),
        'Comunicados del colegio',
    )


@login_required
def tutor_comunicados(request):
    if request.user.rol != 'tutor':
        return redirect('core:home')

    tutor = get_object_or_404(Tutor, usuario=request.user)

    from .services.comunicados import comunicados_para_tutor

    return _portal_comunicados(
        request,
        comunicados_para_tutor(tutor),
        'Comunicados del colegio',
    )
