from django.shortcuts import render
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from core.decorators import centro_required, role_required

from .models import Bitacora


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
@centro_required
def bitacora_list(request):
    """Bitácora de auditoría del centro (director / admin / superadmin)."""

    centro = request.centro

    q = request.GET.get('q', '').strip()
    accion = request.GET.get('accion', '').strip()
    riesgo = request.GET.get('riesgo', '').strip()
    modulo = request.GET.get('modulo', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    base = Bitacora.objects.filter(
        centro=centro,
    ).select_related('usuario')

    modulos = list(
        base.values_list('modulo', flat=True)
        .distinct()
        .order_by('modulo')
    )

    queryset = base

    if q:
        queryset = queryset.filter(
            Q(usuario__username__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(modelo__icontains=q) |
            Q(objeto_id__icontains=q) |
            Q(ip__icontains=q)
        )

    if accion:
        queryset = queryset.filter(accion=accion)

    if riesgo:
        queryset = queryset.filter(riesgo=riesgo)

    if modulo:
        queryset = queryset.filter(modulo__iexact=modulo)

    if desde:
        queryset = queryset.filter(fecha__date__gte=desde)

    if hasta:
        queryset = queryset.filter(fecha__date__lte=hasta)

    total = queryset.count()
    eventos_hoy = queryset.filter(
        fecha__date=timezone.localdate()
    ).count()
    riesgos_alto = queryset.filter(
        riesgo__in=['ALTO', 'CRITICO']
    ).count()

    queryset = queryset.order_by('-fecha', '-id')

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'auditoria/bitacora.html', {
        'centro': centro,
        'registros': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'accion': accion,
        'riesgo': riesgo,
        'modulo': modulo,
        'desde': desde,
        'hasta': hasta,
        'acciones': Bitacora.ACCIONES,
        'riesgos': Bitacora.NIVELES_RIESGO,
        'modulos': modulos,
        'total': total,
        'eventos_hoy': eventos_hoy,
        'riesgos_alto': riesgos_alto,
    })
