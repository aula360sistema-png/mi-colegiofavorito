from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.models import AnioEscolar
from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from .models import Factura, TipoComprobante
from .services import facturas_del_centro, metricas_facturas

ROLES_FACTURACION = ('director', 'admin', 'superadmin', 'cajero', 'secretaria')
ROLES_GESTION = ('director', 'admin', 'superadmin', 'secretaria')


def _base_ctx(request):
    return {
        'centro': get_centro_activo(request),
    }


@login_required
@centro_required
@role_required(*ROLES_FACTURACION)
def facturacion_inicio(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro)
    hoy = timezone.localdate()

    m = metricas_facturas(centro, anio)

    ctx = _base_ctx(request)
    ctx.update({
        'anio': anio,
        'total_facturado': m['total_facturado'],
        'total_itbis': m['total_itbis'],
        'cantidad_facturas': m['cantidad_facturas'],
        'facturas_hoy': m['facturas_hoy'],
        'facturas_recientes': m['facturas_recientes'],
        'config': getattr(centro, 'configuracioncentro', None),
        'hoy': hoy,
    })

    return render(request, 'facturacion/facturacion_inicio.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_FACTURACION)
def lista_facturas(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro)

    facturas = facturas_del_centro(centro)

    q = request.GET.get('q', '').strip()
    tipo_id = request.GET.get('tipo', '')
    anio_id = request.GET.get('anio', '')
    solo_itbis = request.GET.get('itbis', '') == '1'

    if q:
        q = q.lower()
        facturas = [
            f for f in facturas
            if q in (f.estudiante.matricula or '').lower()
            or q in (f.estudiante.primer_nombre or '').lower()
            or q in (f.estudiante.primer_apellido or '').lower()
            or q in (f.ncf or '').lower()
        ]

    if tipo_id:
        facturas = [f for f in facturas if str(f.tipo_id or '') == str(tipo_id)]

    if anio_id:
        anio_obj = AnioEscolar.objects.filter(pk=anio_id, centro=centro).first()
        if anio_obj:
            facturas = [
                f for f in facturas
                if anio_obj.fecha_inicio <= f.fecha <= anio_obj.fecha_fin
            ]

    if solo_itbis:
        facturas = [f for f in facturas if f.aplica_itbis]

    facturas = sorted(facturas, key=lambda f: (f.fecha, f.id), reverse=True)

    total_facturado = sum(f.total for f in facturas) or 0
    total_itbis = sum(f.itbis for f in facturas) or 0
    cantidad = len(facturas)

    ctx = _base_ctx(request)
    ctx.update({
        'facturas': facturas,
        'tipos': TipoComprobante.objects.filter(activo=True),
        'anios': AnioEscolar.objects.filter(centro=centro),
        'anio': anio,
        'total_facturado': total_facturado,
        'total_itbis': total_itbis,
        'cantidad': cantidad,
        'q': q,
        'tipo_seleccionado': tipo_id,
        'anio_seleccionado': anio_id,
        'solo_itbis': solo_itbis,
    })

    return render(request, 'facturacion/lista_facturas.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_FACTURACION)
def detalle_factura(request, factura_id):
    centro = get_centro_activo(request)

    factura = get_object_or_404(
        Factura.objects.select_related(
            'centro', 'estudiante', 'tipo', 'pago'
        ),
        pk=factura_id,
        centro=centro,
    )

    ctx = _base_ctx(request)
    ctx.update({
        'factura': factura,
        'config': getattr(centro, 'configuracioncentro', None),
    })

    return render(request, 'facturacion/detalle_factura.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_GESTION)
def lista_comprobantes(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        tipo_id = request.POST.get('tipo_id')
        tipo = get_object_or_404(
            TipoComprobante,
            pk=tipo_id,
        )
        tipo.activo = not tipo.activo
        tipo.save()
        estado = 'activado' if tipo.activo else 'desactivado'
        from django.contrib import messages
        messages.success(
            request,
            f"Comprobante {tipo.codigo} · {tipo.nombre} {estado}."
        )
        return redirect('facturacion:lista_comprobantes')

    activos = TipoComprobante.objects.filter(activo=True).count()

    ctx = _base_ctx(request)
    ctx.update({
        'comprobantes': TipoComprobante.objects.all(),
        'activos': activos,
    })

    return render(request, 'facturacion/lista_comprobantes.html', ctx)
