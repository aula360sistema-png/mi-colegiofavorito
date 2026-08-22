from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import role_required
from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from .forms import (
    DestrezaCognitivaForm,
    DiagnosticoCognitivoForm,
    EjercicioForm,
    PlanRefuerzoForm,
    SesionEntrenamientoForm,
    TramoEdadForm,
    UnidadEntrenamientoForm,
)
from .models import (
    DestrezaCognitiva,
    DiagnosticoCognitivo,
    Ejercicio,
    MetricaCognitiva,
    PlanRefuerzo,
    SesionEntrenamiento,
    TramoEdad,
    UnidadEntrenamiento,
)
from .services import (
    diagnosticos_del_centro,
    invalidar_catalogo,
    invalidar_entrenamiento,
    metricas_dashboard,
    metricas_del_centro,
    planes_refuerzo_del_centro,
    sesiones_del_centro,
)

_roles_admin = ('director', 'secretaria', 'admin', 'superadmin')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def inicio(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro) if centro else None
    raw = metricas_dashboard(centro, anio)
    stats = {
        'total_diagnosticos': raw.get('total_diagnosticos', 0),
        'total_sesiones': raw.get('total_sesiones', 0),
        'sesiones_completadas': raw.get('sesiones_completadas', 0),
        'total_planes': raw.get('total_planes', 0),
        'planes_activos': raw.get('planes_activos', 0),
        'ipd_promedio': raw.get('ipd_promedio', 0),
    }
    return render(request, 'entrenamiento/inicio.html', {
        'centro': centro,
        'anio_actual': anio,
        'stats': stats,
    })


# ---------------------------------------------------------------------------
# TramoEdad CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def tramo_list(request):
    queryset = TramoEdad.objects.all().order_by('orden', 'edad_min')
    page_obj = Paginator(queryset, 10).get_page(request.GET.get('page'))
    return render(request, 'entrenamiento/tramo_list.html', {
        'page_obj': page_obj,
    })


@login_required
@role_required(*_roles_admin)
def tramo_create(request):
    if request.method == 'POST':
        form = TramoEdadForm(request.POST)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Tramo de edad creado correctamente.')
            return redirect('entrenamiento:tramo_list')
    else:
        form = TramoEdadForm()
    return render(request, 'entrenamiento/tramo_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def tramo_update(request, pk):
    tramo = get_object_or_404(TramoEdad, pk=pk)
    if request.method == 'POST':
        form = TramoEdadForm(request.POST, instance=tramo)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Tramo de edad actualizado correctamente.')
            return redirect('entrenamiento:tramo_list')
    else:
        form = TramoEdadForm(instance=tramo)
    return render(request, 'entrenamiento/tramo_form.html', {
        'form': form,
        'accion': 'Editar',
        'tramo': tramo,
    })


@login_required
@role_required(*_roles_admin)
def tramo_delete(request, pk):
    tramo = get_object_or_404(TramoEdad, pk=pk)
    if request.method == 'POST':
        tramo.delete()
        invalidar_catalogo()
        messages.success(request, 'Tramo de edad eliminado correctamente.')
        return redirect('entrenamiento:tramo_list')
    return render(request, 'entrenamiento/tramo_confirm_delete.html', {
        'tramo': tramo,
    })


# ---------------------------------------------------------------------------
# DestrezaCognitiva CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def destreza_list(request):
    tramo_id = request.GET.get('tramo', '')
    queryset = DestrezaCognitiva.objects.select_related('tramo').all()
    if tramo_id:
        queryset = queryset.filter(tramo_id=tramo_id)
    queryset = queryset.order_by('tramo__orden', 'orden', 'nombre')
    page_obj = Paginator(queryset, 10).get_page(request.GET.get('page'))
    tramos = TramoEdad.objects.filter(activo=True).order_by('orden')
    return render(request, 'entrenamiento/destreza_list.html', {
        'page_obj': page_obj,
        'tramos': tramos,
        'tramo_seleccionado': tramo_id,
    })


@login_required
@role_required(*_roles_admin)
def destreza_create(request):
    if request.method == 'POST':
        form = DestrezaCognitivaForm(request.POST)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Destreza cognitiva creada correctamente.')
            return redirect('entrenamiento:destreza_list')
    else:
        form = DestrezaCognitivaForm()
    return render(request, 'entrenamiento/destreza_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def destreza_update(request, pk):
    destreza = get_object_or_404(DestrezaCognitiva, pk=pk)
    if request.method == 'POST':
        form = DestrezaCognitivaForm(request.POST, instance=destreza)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Destreza cognitiva actualizada correctamente.')
            return redirect('entrenamiento:destreza_list')
    else:
        form = DestrezaCognitivaForm(instance=destreza)
    return render(request, 'entrenamiento/destreza_form.html', {
        'form': form,
        'accion': 'Editar',
        'destreza': destreza,
    })


@login_required
@role_required(*_roles_admin)
def destreza_delete(request, pk):
    destreza = get_object_or_404(DestrezaCognitiva, pk=pk)
    if request.method == 'POST':
        destreza.delete()
        invalidar_catalogo()
        messages.success(request, 'Destreza cognitiva eliminada correctamente.')
        return redirect('entrenamiento:destreza_list')
    return render(request, 'entrenamiento/destreza_confirm_delete.html', {
        'destreza': destreza,
    })


# ---------------------------------------------------------------------------
# UnidadEntrenamiento CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def unidad_list(request):
    tramo_id = request.GET.get('tramo', '')
    queryset = UnidadEntrenamiento.objects.select_related('tramo').prefetch_related('destrezas').all()
    if tramo_id:
        queryset = queryset.filter(tramo_id=tramo_id)
    queryset = queryset.order_by('tramo__orden', 'numero')
    page_obj = Paginator(queryset, 10).get_page(request.GET.get('page'))
    tramos = TramoEdad.objects.filter(activo=True).order_by('orden')
    return render(request, 'entrenamiento/unidad_list.html', {
        'page_obj': page_obj,
        'tramos': tramos,
        'tramo_seleccionado': tramo_id,
    })


@login_required
@role_required(*_roles_admin)
def unidad_create(request):
    if request.method == 'POST':
        form = UnidadEntrenamientoForm(request.POST)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Unidad de entrenamiento creada correctamente.')
            return redirect('entrenamiento:unidad_list')
    else:
        form = UnidadEntrenamientoForm()
    return render(request, 'entrenamiento/unidad_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def unidad_update(request, pk):
    unidad = get_object_or_404(UnidadEntrenamiento, pk=pk)
    if request.method == 'POST':
        form = UnidadEntrenamientoForm(request.POST, instance=unidad)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Unidad de entrenamiento actualizada correctamente.')
            return redirect('entrenamiento:unidad_list')
    else:
        form = UnidadEntrenamientoForm(instance=unidad)
    return render(request, 'entrenamiento/unidad_form.html', {
        'form': form,
        'accion': 'Editar',
        'unidad': unidad,
    })


@login_required
@role_required(*_roles_admin)
def unidad_delete(request, pk):
    unidad = get_object_or_404(UnidadEntrenamiento, pk=pk)
    if request.method == 'POST':
        unidad.delete()
        invalidar_catalogo()
        messages.success(request, 'Unidad de entrenamiento eliminada correctamente.')
        return redirect('entrenamiento:unidad_list')
    return render(request, 'entrenamiento/unidad_confirm_delete.html', {
        'unidad': unidad,
    })


# ---------------------------------------------------------------------------
# Ejercicio CRUD (list, create, detail, delete — no update)
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def ejercicio_list(request):
    unidad_id = request.GET.get('unidad', '')
    queryset = Ejercicio.objects.select_related('unidad', 'destreza').all()
    if unidad_id:
        queryset = queryset.filter(unidad_id=unidad_id)
    queryset = queryset.order_by('unidad__tramo__orden', 'unidad__numero', 'destreza__orden', 'dificultad')
    page_obj = Paginator(queryset, 10).get_page(request.GET.get('page'))
    unidades = UnidadEntrenamiento.objects.select_related('tramo').filter(activo=True).order_by('tramo__orden', 'numero')
    return render(request, 'entrenamiento/ejercicio_list.html', {
        'page_obj': page_obj,
        'unidades': unidades,
        'unidad_seleccionada': unidad_id,
    })


@login_required
@role_required(*_roles_admin)
def ejercicio_create(request):
    if request.method == 'POST':
        form = EjercicioForm(request.POST)
        if form.is_valid():
            form.save()
            invalidar_catalogo()
            messages.success(request, 'Ejercicio creado correctamente.')
            return redirect('entrenamiento:ejercicio_list')
    else:
        form = EjercicioForm()
    return render(request, 'entrenamiento/ejercicio_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def ejercicio_detail(request, pk):
    ejercicio = get_object_or_404(
        Ejercicio.objects.select_related('unidad', 'destreza', 'unidad__tramo'),
        pk=pk,
    )
    return render(request, 'entrenamiento/ejercicio_detail.html', {
        'obj': ejercicio,
    })


@login_required
@role_required(*_roles_admin)
def ejercicio_delete(request, pk):
    ejercicio = get_object_or_404(Ejercicio, pk=pk)
    if request.method == 'POST':
        ejercicio.delete()
        invalidar_catalogo()
        messages.success(request, 'Ejercicio eliminado correctamente.')
        return redirect('entrenamiento:ejercicio_list')
    return render(request, 'entrenamiento/ejercicio_confirm_delete.html', {
        'ejercicio': ejercicio,
    })


# ---------------------------------------------------------------------------
# DiagnosticoCognitivo CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def diagnostico_list(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro) if centro else None
    diagnosticos = diagnosticos_del_centro(centro, anio)
    page_obj = Paginator(diagnosticos, 15).get_page(request.GET.get('page'))
    return render(request, 'entrenamiento/diagnostico_list.html', {
        'page_obj': page_obj,
        'centro': centro,
        'anio': anio,
    })


@login_required
@role_required(*_roles_admin)
def diagnostico_create(request):
    if request.method == 'POST':
        form = DiagnosticoCognitivoForm(request.POST)
        if form.is_valid():
            form.save()
            centro = get_centro_activo(request)
            if centro:
                invalidar_entrenamiento(centro.id)
            messages.success(request, 'Diagnóstico cognitivo registrado correctamente.')
            return redirect('entrenamiento:diagnostico_list')
    else:
        form = DiagnosticoCognitivoForm()
    return render(request, 'entrenamiento/diagnostico_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def diagnostico_detail(request, pk):
    diagnostico = get_object_or_404(
        DiagnosticoCognitivo.objects.select_related('estudiante', 'tramo', 'anio_escolar'),
        pk=pk,
    )
    return render(request, 'entrenamiento/diagnostico_detail.html', {
        'obj': diagnostico,
    })


@login_required
@role_required(*_roles_admin)
def diagnostico_delete(request, pk):
    diagnostico = get_object_or_404(DiagnosticoCognitivo, pk=pk)
    if request.method == 'POST':
        diagnostico.delete()
        centro = get_centro_activo(request)
        if centro:
            invalidar_entrenamiento(centro.id)
        messages.success(request, 'Diagnóstico cognitivo eliminado correctamente.')
        return redirect('entrenamiento:diagnostico_list')
    return render(request, 'entrenamiento/diagnostico_confirm_delete.html', {
        'diagnostico': diagnostico,
    })


# ---------------------------------------------------------------------------
# SesionEntrenamiento CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def sesion_list(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro) if centro else None
    sesiones = sesiones_del_centro(centro, anio)
    page_obj = Paginator(sesiones, 15).get_page(request.GET.get('page'))
    return render(request, 'entrenamiento/sesion_list.html', {
        'page_obj': page_obj,
        'centro': centro,
        'anio': anio,
    })


@login_required
@role_required(*_roles_admin)
def sesion_create(request):
    if request.method == 'POST':
        form = SesionEntrenamientoForm(request.POST)
        if form.is_valid():
            form.save()
            centro = get_centro_activo(request)
            if centro:
                invalidar_entrenamiento(centro.id)
            messages.success(request, 'Sesión de entrenamiento creada correctamente.')
            return redirect('entrenamiento:sesion_list')
    else:
        form = SesionEntrenamientoForm()
    return render(request, 'entrenamiento/sesion_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def sesion_detail(request, pk):
    sesion = get_object_or_404(
        SesionEntrenamiento.objects.select_related(
            'estudiante', 'unidad', 'unidad__tramo', 'anio_escolar',
        ),
        pk=pk,
    )
    intentos = sesion.intentos.select_related('ejercicio', 'ejercicio__destreza').order_by('id')
    aciertos = intentos.filter(acierto=True).count()
    total = intentos.count()
    return render(request, 'entrenamiento/sesion_detail.html', {
        'obj': sesion,
        'intentos': intentos,
        'aciertos': aciertos,
        'total': total,
    })


@login_required
@role_required(*_roles_admin)
def sesion_delete(request, pk):
    sesion = get_object_or_404(SesionEntrenamiento, pk=pk)
    if request.method == 'POST':
        sesion.delete()
        centro = get_centro_activo(request)
        if centro:
            invalidar_entrenamiento(centro.id)
        messages.success(request, 'Sesión de entrenamiento eliminada correctamente.')
        return redirect('entrenamiento:sesion_list')
    return render(request, 'entrenamiento/sesion_confirm_delete.html', {
        'sesion': sesion,
    })


# ---------------------------------------------------------------------------
# MetricaCognitiva (read-only)
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def metrica_list(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro) if centro else None
    metricas = metricas_del_centro(centro, anio)
    page_obj = Paginator(metricas, 15).get_page(request.GET.get('page'))
    return render(request, 'entrenamiento/metrica_list.html', {
        'page_obj': page_obj,
        'centro': centro,
        'anio': anio,
    })


@login_required
@role_required(*_roles_admin)
def metrica_detail(request, pk):
    metrica = get_object_or_404(
        MetricaCognitiva.objects.select_related('estudiante', 'periodo', 'tramo', 'anio_escolar'),
        pk=pk,
    )
    return render(request, 'entrenamiento/metrica_detail.html', {
        'obj': metrica,
    })


# ---------------------------------------------------------------------------
# PlanRefuerzo CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def plan_list(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro) if centro else None
    planes = planes_refuerzo_del_centro(centro, anio)
    page_obj = Paginator(planes, 15).get_page(request.GET.get('page'))
    return render(request, 'entrenamiento/plan_list.html', {
        'page_obj': page_obj,
        'centro': centro,
        'anio': anio,
    })


@login_required
@role_required(*_roles_admin)
def plan_create(request):
    if request.method == 'POST':
        form = PlanRefuerzoForm(request.POST)
        if form.is_valid():
            form.save()
            centro = get_centro_activo(request)
            if centro:
                invalidar_entrenamiento(centro.id)
            messages.success(request, 'Plan de refuerzo creado correctamente.')
            return redirect('entrenamiento:plan_list')
    else:
        form = PlanRefuerzoForm()
    return render(request, 'entrenamiento/plan_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required(*_roles_admin)
def plan_detail(request, pk):
    plan = get_object_or_404(
        PlanRefuerzo.objects.select_related('estudiante', 'unidad', 'unidad__tramo', 'anio_escolar'),
        pk=pk,
    )
    items = plan.items.select_related('destreza', 'ejercicio').order_by('orden')
    return render(request, 'entrenamiento/plan_detail.html', {
        'obj': plan,
        'items': items,
    })


@login_required
@role_required(*_roles_admin)
def plan_update_estado(request, pk):
    plan = get_object_or_404(PlanRefuerzo, pk=pk)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado', '')
        estados_validos = [c[0] for c in PlanRefuerzo.ESTADOS]
        if nuevo_estado in estados_validos:
            plan.estado = nuevo_estado
            plan.save()
            centro = get_centro_activo(request)
            if centro:
                invalidar_entrenamiento(centro.id)
            messages.success(request, f'Estado del plan actualizado a "{plan.get_estado_display()}".')
        else:
            messages.error(request, 'Estado no válido.')
    return redirect('entrenamiento:plan_detail', pk=pk)


@login_required
@role_required(*_roles_admin)
def plan_delete(request, pk):
    plan = get_object_or_404(PlanRefuerzo, pk=pk)
    if request.method == 'POST':
        plan.delete()
        centro = get_centro_activo(request)
        if centro:
            invalidar_entrenamiento(centro.id)
        messages.success(request, 'Plan de refuerzo eliminado correctamente.')
        return redirect('entrenamiento:plan_list')
    return render(request, 'entrenamiento/plan_confirm_delete.html', {
        'plan': plan,
    })


# ---------------------------------------------------------------------------
# AJAX — Destrezas por tramo
# ---------------------------------------------------------------------------

@login_required
@role_required(*_roles_admin)
def api_destrezas_por_tramo(request):
    tramo_id = request.GET.get('tramo_id')
    if not tramo_id:
        return JsonResponse({'destrezas': []})
    destrezas = DestrezaCognitiva.objects.filter(
        tramo_id=tramo_id, activo=True,
    ).order_by('orden', 'nombre').values('id', 'nombre', 'categoria')
    return JsonResponse({'destrezas': list(destrezas)})
