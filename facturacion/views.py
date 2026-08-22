from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.models import AnioEscolar
from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from .models import Factura, TipoComprobante
from .services import facturas_del_centro, metricas_facturas, _redondear as redondear

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


# =========================
# CREAR FACTURA MANUAL
# =========================

@login_required
@centro_required
@role_required(*ROLES_GESTION)
def crear_factura(request):
    centro = get_centro_activo(request)

    from estudiantes.models import Estudiante
    from .models import SecuenciaNCF, TASA_ITBIS

    if request.method == 'POST':
        estudiante_id = request.POST.get('estudiante')
        tipo_id = request.POST.get('tipo')
        descripcion = request.POST.get('descripcion', '').strip()
        cantidad = request.POST.get('cantidad', '1')
        precio = request.POST.get('precio', '0')
        aplica_itbis = request.POST.get('aplica_itbis') == 'on'

        estudiante = get_object_or_404(Estudiante, pk=estudiante_id, centro=centro)
        tipo = get_object_or_404(TipoComprobante, pk=tipo_id, activo=True)

        from decimal import Decimal, ROUND_HALF_UP
        try:
            cantidad = int(cantidad)
            precio = Decimal(precio)
        except (ValueError, TypeError):
            from django.contrib import messages
            messages.error(request, 'Cantidad o precio inválido.')
            return redirect('facturacion:crear_factura')

        subtotal = redondear(precio * cantidad)
        itbis = redondear(subtotal * TASA_ITBIS) if aplica_itbis else Decimal('0.00')
        total = redondear(subtotal + itbis)

        from .services import siguiente_ncf
        ncf = siguiente_ncf(centro, tipo) if tipo else ''

        from django.db import transaction
        with transaction.atomic():
            from .models import FacturaItem
            factura = Factura.objects.create(
                centro=centro,
                ncf=ncf,
                tipo=tipo,
                estudiante=estudiante,
                subtotal=subtotal,
                itbis=itbis,
                total=total,
                aplica_itbis=aplica_itbis,
                fecha=timezone.localdate(),
                creado_por=request.user,
            )
            FacturaItem.objects.create(
                factura=factura,
                descripcion=descripcion or 'Servicio escolar',
                cantidad=cantidad,
                precio=precio,
                subtotal=subtotal,
            )

        from .services import invalidar_facturas_centro
        invalidar_facturas_centro(centro.id)

        from django.contrib import messages
        messages.success(
            request,
            f'Factura {ncf} creada por RD$ {total:,.2f}.'
        )
        return redirect('facturacion:detalle_factura', factura_id=factura.pk)

    estudiantes = Estudiante.objects.filter(
        centro=centro, estado='activo'
    ).order_by('primer_nombre', 'primer_apellido')

    tipos = TipoComprobante.objects.filter(activo=True)

    ctx = _base_ctx(request)
    ctx.update({
        'estudiantes': estudiantes,
        'tipos': tipos,
    })

    return render(request, 'facturacion/crear_factura.html', ctx)


# =========================
# SECUENCIAS NCF
# =========================

@login_required
@centro_required
@role_required(*ROLES_GESTION)
def secuencias_ncf(request):
    centro = get_centro_activo(request)

    from .models import SecuenciaNCF

    secuencias = SecuenciaNCF.objects.filter(
        centro=centro
    ).select_related('tipo').order_by('tipo__codigo')

    if request.method == 'POST':
        tipo_id = request.POST.get('tipo_id')
        tipo = get_object_or_404(TipoComprobante, pk=tipo_id, activo=True)

        secuencia, created = SecuenciaNCF.objects.get_or_create(
            centro=centro,
            tipo=tipo,
            defaults={'ultimo_numero': 0, 'activo': True},
        )
        if not created:
            secuencia.activo = not secuencia.activo
            secuencia.save(update_fields=['activo'])

        estado = 'activada' if secuencia.activo else 'desactivada'
        from django.contrib import messages
        messages.success(
            request,
            f'Secuencia NCF {tipo.codigo} · {tipo.nombre} {estado}.'
        )
        return redirect('facturacion:secuencias_ncf')

    from django.contrib import messages
    ctx = _base_ctx(request)
    ctx.update({
        'secuencias': secuencias,
        'tipos_disponibles': TipoComprobante.objects.filter(activo=True),
    })

    return render(request, 'facturacion/secuencias_ncf.html', ctx)
