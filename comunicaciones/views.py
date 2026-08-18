from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import centro_required, role_required
from tutores.models import Tutor

from .forms import CampaniaForm
from .models import Campania
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