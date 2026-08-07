from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone

from core.decorators import centro_required, role_required
from core.models import AnioEscolar
from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from academico.models import Grado, Seccion
from estudiantes.models import Estudiante, Inscripcion

from .forms import (
    AperturaCajaForm,
    CajaForm,
    ConceptoPagoForm,
    CierreCajaForm,
    EgresoForm,
    PagoForm,
)
from .models import (
    AsignacionConcepto,
    Caja,
    ConceptoPago,
    Egreso,
    Pago,
    SesionCaja,
)
from .services import (
    balance_por_concepto,
    calcular_cuentas_por_cobrar_detalle,
    cajas_disponibles,
    obtener_sesion_abierta,
    saldo_por_concepto,
    siguiente_recibo,
    tiene_sesion_abierta,
)

ROLES_CAJA = ('director', 'admin', 'superadmin', 'cajero')
ROLES_GESTION_CAJAS = ('director', 'admin', 'superadmin')


def _base_ctx(request):
    centro = get_centro_activo(request)
    return {
        'centro': centro,
        'sesion_abierta': obtener_sesion_abierta(centro, request.user),
    }


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def caja_inicio(request):
    centro = get_centro_activo(request)
    sesion = obtener_sesion_abierta(centro, request.user)
    hoy = timezone.localdate()

    ctx = _base_ctx(request)

    ctx.update({
        'hoy': hoy,
        'entradas_hoy': Pago.objects.filter(
            centro=centro, fecha=hoy
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'salidas_hoy': Egreso.objects.filter(
            centro=centro, fecha=hoy
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'pagos_hoy': Pago.objects.filter(
            centro=centro, fecha=hoy
        ).select_related('estudiante', 'concepto').order_by('-id')[:6],
        'egresos_hoy': Egreso.objects.filter(
            centro=centro, fecha=hoy
        ).order_by('-id')[:6],
        'total_entradas': Pago.objects.filter(centro=centro)
        .aggregate(t=Sum('monto'))['t'] or 0,
        'total_salidas': Egreso.objects.filter(centro=centro)
        .aggregate(t=Sum('monto'))['t'] or 0,
        'cajas': Caja.objects.filter(centro=centro).prefetch_related('sesiones'),
        'ultimas_sesiones': SesionCaja.objects.filter(
            centro=centro
        ).select_related('caja')[:5],
        'anio_actual': obtener_anio_activo(centro),
    })

    return render(request, 'caja/caja_inicio.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def abrir_caja(request):
    centro = get_centro_activo(request)

    if tiene_sesion_abierta(centro, request.user):
        messages.warning(request, "Ya tienes una caja abierta.")
        return redirect('caja:caja_inicio')

    disponibles = cajas_disponibles(centro)

    if not disponibles.exists():
        messages.warning(
            request,
            "No hay cajas activas disponibles para abrir."
        )
        return redirect('caja:caja_inicio')

    if request.method == 'POST':
        form = AperturaCajaForm(request.POST, centro=centro)

        if form.is_valid():
            sesion = form.save(commit=False)
            sesion.centro = centro
            sesion.usuario_apertura = request.user
            sesion.estado = 'abierta'
            sesion.save()

            messages.success(
                request,
                f"Caja '{sesion.caja}' abierta correctamente."
            )
            return redirect('caja:caja_inicio')
    else:
        form = AperturaCajaForm(centro=centro)

    ctx = _base_ctx(request)
    ctx.update({
        'form': form,
        'cajas': disponibles,
    })
    return render(request, 'caja/abrir_caja.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def cerrar_caja(request):
    centro = get_centro_activo(request)
    sesion = obtener_sesion_abierta(centro, request.user)

    if not sesion:
        messages.warning(request, "No tienes una caja abierta.")
        return redirect('caja:caja_inicio')

    if request.method == 'POST':
        form = CierreCajaForm(request.POST)

        if form.is_valid():
            sesion.arqueo = form.cleaned_data['arqueo']
            sesion.nota_cierre = form.cleaned_data['nota_cierre']
            sesion.diferencia = (
                form.cleaned_data['arqueo'] - sesion.efectivo_esperado()
            )
            sesion.fecha_cierre = timezone.now()
            sesion.usuario_cierre = request.user
            sesion.estado = 'cerrada'
            sesion.save()

            messages.success(request, "Caja cerrada correctamente.")
            return redirect('caja:detalle_sesion', sesion_id=sesion.id)
    else:
        form = CierreCajaForm()

    ctx = _base_ctx(request)
    ctx.update({
        'form': form,
        'sesion': sesion,
    })
    return render(request, 'caja/cerrar_caja.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_GESTION_CAJAS)
def lista_cajas(request):
    centro = get_centro_activo(request)

    cajas = Caja.objects.filter(centro=centro).prefetch_related('sesiones')

    ctx = _base_ctx(request)
    ctx['cajas'] = cajas
    return render(request, 'caja/lista_cajas.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_GESTION_CAJAS)
def crear_caja(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = CajaForm(request.POST)

        if form.is_valid():
            caja = form.save(commit=False)
            caja.centro = centro
            caja.save()

            messages.success(
                request,
                f"Caja '{caja.nombre}' creada correctamente."
            )
            return redirect('caja:lista_cajas')
    else:
        form = CajaForm()

    ctx = _base_ctx(request)
    ctx['form'] = form
    return render(request, 'caja/caja_form.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_GESTION_CAJAS)
def editar_caja(request, caja_id):
    centro = get_centro_activo(request)
    caja = get_object_or_404(Caja, pk=caja_id, centro=centro)

    if request.method == 'POST':
        form = CajaForm(request.POST, instance=caja)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Caja '{caja.nombre}' actualizada correctamente."
            )
            return redirect('caja:lista_cajas')
    else:
        form = CajaForm(instance=caja)

    ctx = _base_ctx(request)
    ctx.update({
        'form': form,
        'caja': caja,
    })
    return render(request, 'caja/caja_form.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_GESTION_CAJAS)
def alternar_caja(request, caja_id):
    centro = get_centro_activo(request)
    caja = get_object_or_404(Caja, pk=caja_id, centro=centro)

    if caja.activa and caja.sesion_abierta:
        messages.warning(
            request,
            f"La caja '{caja.nombre}' tiene una sesión abierta; no se puede desactivar."
        )
        return redirect('caja:lista_cajas')

    caja.activa = not caja.activa
    caja.save()

    estado = 'activada' if caja.activa else 'desactivada'
    messages.success(
        request,
        f"Caja '{caja.nombre}' {estado}."
    )
    return redirect('caja:lista_cajas')


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def lista_pagos(request):
    centro = get_centro_activo(request)

    pagos = Pago.objects.filter(centro=centro).select_related(
        'estudiante', 'concepto', 'sesion'
    )

    q = request.GET.get('q', '').strip()
    concepto_id = request.GET.get('concepto')
    anio = request.GET.get('anio')
    sesion_id = request.GET.get('sesion')

    if q:
        pagos = pagos.filter(
            Q(estudiante__matricula__icontains=q) |
            Q(estudiante__primer_nombre__icontains=q) |
            Q(estudiante__primer_apellido__icontains=q)
        )

    if concepto_id:
        pagos = pagos.filter(concepto_id=concepto_id)

    if anio:
        pagos = pagos.filter(fecha__year=anio)

    if sesion_id:
        pagos = pagos.filter(sesion_id=sesion_id)

    pagos = pagos.order_by('-fecha', '-id')

    total_general = pagos.aggregate(total=Sum('monto'))['total'] or 0

    por_metodo = (
        pagos.values('metodo_pago')
        .annotate(total=Sum('monto'), cantidad=Count('id'))
    )

    anios_disponibles = (
        Pago.objects.filter(centro=centro)
        .dates('fecha', 'year')
    )

    ctx = _base_ctx(request)
    ctx.update({
        'pagos': pagos,
        'conceptos': ConceptoPago.objects.filter(centro=centro),
        'total_general': total_general,
        'por_metodo': por_metodo,
        'anios_disponibles': [d.year for d in anios_disponibles],
        'q': q,
        'concepto_seleccionado': concepto_id,
        'anio_seleccionado': anio,
        'sesion_seleccionada': sesion_id,
    })

    return render(request, 'caja/lista_pagos.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def registrar_pago(request, estudiante_id=None, concepto_id=None):
    centro = get_centro_activo(request)

    sesion = obtener_sesion_abierta(centro, request.user)
    if not sesion:
        messages.warning(
            request,
            "Debes abrir la caja antes de registrar pagos."
        )
        return redirect('caja:abrir_caja')

    estudiante = None
    concepto = None

    if estudiante_id:
        estudiante = get_object_or_404(
            Estudiante,
            pk=estudiante_id,
            centro=centro
        )

    if concepto_id:
        concepto = get_object_or_404(
            ConceptoPago,
            pk=concepto_id,
            centro=centro,
            activo=True,
        )

    if not ConceptoPago.objects.filter(centro=centro, activo=True).exists():
        messages.warning(
            request,
            "No hay conceptos de pago configurados. Créalos primero."
        )
        return redirect('caja:lista_conceptos')

    anio_activo = obtener_anio_activo(centro)

    if request.method == 'POST':
        form = PagoForm(request.POST, centro=centro)

        if form.is_valid():
            pago = form.save(commit=False)
            pago.centro = centro
            pago.creado_por = request.user
            pago.sesion = sesion

            duplicado = Pago.objects.filter(
                centro=centro,
                sesion=sesion,
                estudiante=pago.estudiante,
                concepto=pago.concepto,
                monto=pago.monto,
                fecha=pago.fecha,
                creado_por=request.user,
                created_at__gte=timezone.now() - timedelta(seconds=10),
            ).exists()

            if duplicado:
                messages.info(
                    request,
                    "Ese pago ya fue registrado. No se generó un duplicado."
                )
                return redirect('caja:lista_pagos')

            pago.recibo = siguiente_recibo(Pago, centro)

            saldo_antes = 0
            if anio_activo:
                _, _, saldo_antes = saldo_por_concepto(
                    centro,
                    pago.estudiante,
                    pago.concepto,
                    anio_activo,
                )

            pago.save()

            restante = max(saldo_antes - pago.monto, 0)
            if restante <= 0:
                messages.success(
                    request,
                    f"Pago completado. Recibo No. {pago.recibo}"
                )
            else:
                messages.info(
                    request,
                    f"Abono registrado. Recibo No. {pago.recibo} · "
                    f"Pendiente RD$ {restante:,.2f}"
                )

            return redirect('caja:lista_pagos')

    else:
        initial = {'fecha': timezone.localdate()}

        if estudiante:
            initial['estudiante'] = estudiante

        if concepto:
            initial['concepto'] = concepto
            monto_pendiente = None
            if estudiante and anio_activo:
                _, _, monto_pendiente = saldo_por_concepto(
                    centro,
                    estudiante,
                    concepto,
                    anio_activo,
                )
            if monto_pendiente:
                initial['monto'] = monto_pendiente
            else:
                initial['monto'] = concepto.monto

        form = PagoForm(centro=centro, initial=initial)

    ctx = _base_ctx(request)
    ctx.update({
        'form': form,
        'estudiante': estudiante,
        'hoy': timezone.localdate(),
        'anio_activo': obtener_anio_activo(centro),
        'recibo_siguiente': siguiente_recibo(Pago, centro),
        'estudiantes_disponibles': (
            Estudiante.objects.filter(centro=centro)
            .order_by('primer_apellido', 'primer_nombre')
        ),
    })

    return render(request, 'caja/registrar_pago.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def api_balance_pago(request, estudiante_id):
    """Devuelve el balance por concepto del estudiante en el año activo."""
    centro = get_centro_activo(request)
    estudiante = get_object_or_404(
        Estudiante,
        pk=estudiante_id,
        centro=centro
    )

    anio = obtener_anio_activo(centro)
    if not anio:
        return JsonResponse({
            'estudiante': estudiante.nombre_completo(),
            'matricula': estudiante.matricula,
            'anio': None,
            'enrolado': False,
            'conceptos': [],
        })

    inscrito = Inscripcion.objects.filter(
        centro=centro,
        anio_escolar=anio,
        estudiante=estudiante,
    ).exists()

    filas = balance_por_concepto(centro, estudiante, anio)

    conceptos = [{
        'id': f['concepto'].id,
        'nombre': f['concepto'].nombre,
        'monto': float(f['concepto'].monto),
        'esperado': float(f['esperado']),
        'pagado': float(f['pagado']),
        'saldo': float(f['saldo']),
        'es_recurrente': f['concepto'].es_recurrente,
    } for f in filas]

    return JsonResponse({
        'estudiante': estudiante.nombre_completo(),
        'matricula': estudiante.matricula,
        'anio': anio.nombre,
        'enrolado': inscrito,
        'conceptos': conceptos,
    })


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def registrar_egreso(request):
    centro = get_centro_activo(request)

    sesion = obtener_sesion_abierta(centro, request.user)
    if not sesion:
        messages.warning(
            request,
            "Debes abrir la caja antes de registrar salidas."
        )
        return redirect('caja:abrir_caja')

    if request.method == 'POST':
        form = EgresoForm(request.POST)

        if form.is_valid():
            egreso = form.save(commit=False)
            egreso.centro = centro
            egreso.sesion = sesion
            egreso.creado_por = request.user
            egreso.recibo = siguiente_recibo(Egreso, centro)
            egreso.save()

            messages.success(
                request,
                f"Salida registrada. Recibo No. E-{egreso.recibo}"
            )
            return redirect('caja:lista_egresos')
    else:
        form = EgresoForm(initial={'fecha': timezone.localdate()})

    ctx = _base_ctx(request)
    ctx['form'] = form
    return render(request, 'caja/egreso_form.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def lista_egresos(request):
    centro = get_centro_activo(request)

    egresos = Egreso.objects.filter(centro=centro).select_related('sesion')

    q = request.GET.get('q', '').strip()
    anio = request.GET.get('anio')

    if q:
        egresos = egresos.filter(
            Q(concepto__icontains=q) |
            Q(beneficiario__icontains=q) |
            Q(nota__icontains=q)
        )

    if anio:
        egresos = egresos.filter(fecha__year=anio)

    egresos = egresos.order_by('-fecha', '-id')

    total_general = egresos.aggregate(total=Sum('monto'))['total'] or 0

    anios_disponibles = (
        Egreso.objects.filter(centro=centro).dates('fecha', 'year')
    )

    ctx = _base_ctx(request)
    ctx.update({
        'egresos': egresos,
        'total_general': total_general,
        'anios_disponibles': [d.year for d in anios_disponibles],
        'q': q,
        'anio_seleccionado': anio,
    })

    return render(request, 'caja/lista_egresos.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def recibo_pago(request, pago_id):
    centro = get_centro_activo(request)

    pago = get_object_or_404(
        Pago,
        pk=pago_id,
        centro=centro
    )

    ctx = _base_ctx(request)
    ctx['pago'] = pago
    return render(request, 'caja/recibo_pago.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def lista_conceptos(request):
    centro = get_centro_activo(request)

    conceptos = ConceptoPago.objects.filter(centro=centro)

    ctx = _base_ctx(request)
    ctx['conceptos'] = conceptos
    return render(request, 'caja/lista_conceptos.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def crear_concepto(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = ConceptoPagoForm(request.POST)

        if form.is_valid():
            concepto = form.save(commit=False)
            concepto.centro = centro
            concepto.save()

            messages.success(request, "Concepto creado correctamente.")
            return redirect('caja:lista_conceptos')

    else:
        form = ConceptoPagoForm()

    ctx = _base_ctx(request)
    ctx['form'] = form
    return render(request, 'caja/concepto_form.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def cuentas_por_cobrar(request):
    centro = get_centro_activo(request)
    anio = obtener_anio_activo(centro)

    if not anio:
        messages.warning(request, "No hay año escolar activo.")
        anio = None

    filas = (
        calcular_cuentas_por_cobrar_detalle(centro, anio)
        if anio else []
    )

    q = request.GET.get('q', '').strip()
    if q:
        filas = [
            f for f in filas
            if q.lower() in f['estudiante'].nombre_completo().lower()
            or q.lower() in f['estudiante'].matricula.lower()
        ]

    total_por_cobrar = sum(f['saldo'] for f in filas)

    ctx = _base_ctx(request)
    ctx.update({
        'anio': anio,
        'cuentas': filas,
        'total_por_cobrar': total_por_cobrar,
        'q': q,
    })

    return render(request, 'caja/cuentas_por_cobrar.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def asignaciones_conceptos(request):
    centro = get_centro_activo(request)
    anio_activo = obtener_anio_activo(centro)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'eliminar':
            asig_id = request.POST.get('asignacion_id')
            if asig_id:
                AsignacionConcepto.objects.filter(
                    id=asig_id,
                    centro=centro,
                ).delete()
                messages.success(
                    request, "Asignación eliminada correctamente."
                )
            return redirect('caja:asignaciones_conceptos')

        concepto_id = request.POST.get('concepto')
        anio_id = request.POST.get('anio_escolar')
        estudiante_ids = request.POST.getlist('estudiantes')

        try:
            concepto = ConceptoPago.objects.get(
                pk=concepto_id,
                centro=centro,
            )
            anio_obj = AnioEscolar.objects.get(
                pk=anio_id,
                centro=centro,
            )
        except (ConceptoPago.DoesNotExist, AnioEscolar.DoesNotExist):
            messages.error(request, "Datos de asignación inválidos.")
            return redirect('caja:asignaciones_conceptos')

        if not estudiante_ids:
            messages.warning(
                request, "Selecciona al menos un estudiante."
            )
            return redirect('caja:asignaciones_conceptos')

        creadas = 0
        ya_existentes = 0

        for sid in estudiante_ids:
            _, created = AsignacionConcepto.objects.get_or_create(
                centro=centro,
                estudiante_id=sid,
                concepto=concepto,
                anio_escolar=anio_obj,
                defaults={'activo': True},
            )
            if created:
                creadas += 1
            else:
                ya_existentes += 1

        if creadas:
            messages.success(
                request,
                f"'{concepto.nombre}' asignado a {creadas} estudiante(s).",
            )
        if ya_existentes:
            messages.info(
                request,
                f"{ya_existentes} ya tenían el concepto asignado.",
            )

        return redirect('caja:asignaciones_conceptos')

    anio_id = (
        request.GET.get('anio_escolar')
        or request.GET.get('anio')
        or (anio_activo.id if anio_activo else None)
    )
    grado_id = request.GET.get('grado', '')
    seccion_id = request.GET.get('seccion', '')
    concepto_id = request.GET.get('concepto', '')

    anio_obj = (
        AnioEscolar.objects.filter(pk=anio_id, centro=centro).first()
        if anio_id
        else None
    )

    filas = []
    if anio_obj:
        inscripciones = (
            Inscripcion.objects.filter(
                centro=centro,
                anio_escolar=anio_obj,
            )
            .select_related('estudiante', 'grado', 'seccion')
        )
        if grado_id:
            inscripciones = inscripciones.filter(grado_id=grado_id)
        if seccion_id:
            inscripciones = inscripciones.filter(seccion_id=seccion_id)

        vistos = set()
        for ins in inscripciones:
            if ins.estudiante_id in vistos:
                continue
            vistos.add(ins.estudiante_id)
            filas.append({
                'estudiante': ins.estudiante,
                'grado': ins.grado,
                'seccion': ins.seccion,
            })

        if not grado_id and not seccion_id:
            for est in (
                Estudiante.objects.filter(centro=centro)
                .exclude(id__in=vistos)
                .order_by('primer_apellido', 'primer_nombre')
            ):
                filas.append({
                    'estudiante': est,
                    'grado': None,
                    'seccion': None,
                })

    filas.sort(
        key=lambda f: (
            f['estudiante'].primer_apellido,
            f['estudiante'].primer_nombre,
        )
    )

    ya_asignados = set()
    if anio_obj and concepto_id:
        ya_asignados = set(
            AsignacionConcepto.objects.filter(
                centro=centro,
                anio_escolar=anio_obj,
                concepto_id=concepto_id,
            ).values_list('estudiante_id', flat=True)
        )

    for f in filas:
        f['asignado'] = f['estudiante'].id in ya_asignados

    asignaciones = (
        AsignacionConcepto.objects.filter(centro=centro)
        .select_related('estudiante', 'concepto', 'anio_escolar')
    )
    if anio_obj:
        asignaciones = asignaciones.filter(anio_escolar=anio_obj)

    ctx = _base_ctx(request)
    ctx.update({
        'anios': AnioEscolar.objects.filter(centro=centro),
        'conceptos': ConceptoPago.objects.filter(centro=centro),
        'grados': Grado.objects.filter(nivel__centro=centro),
        'secciones': Seccion.objects.filter(grado__nivel__centro=centro),
        'filas': filas,
        'asignaciones': asignaciones,
        'anio': anio_obj or anio_activo,
        'anio_seleccionado': str(anio_obj.id) if anio_obj else '',
        'grado_seleccionado': grado_id,
        'seccion_seleccionada': seccion_id,
        'concepto_seleccionado': concepto_id,
    })

    return render(request, 'caja/asignaciones_conceptos.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def reporte_diario(request):
    centro = get_centro_activo(request)

    fecha_param = request.GET.get('fecha', '')
    try:
        fecha = (
            timezone.datetime.strptime(fecha_param, '%Y-%m-%d').date()
            if fecha_param
            else timezone.localdate()
        )
    except ValueError:
        fecha = timezone.localdate()

    pagos = Pago.objects.filter(centro=centro, fecha=fecha)
    egresos = Egreso.objects.filter(centro=centro, fecha=fecha)

    caja_id = request.GET.get('caja')
    if caja_id:
        pagos = pagos.filter(sesion__caja_id=caja_id)
        egresos = egresos.filter(sesion__caja_id=caja_id)

    entradas = pagos.aggregate(t=Sum('monto'))['t'] or 0
    salidas = egresos.aggregate(t=Sum('monto'))['t'] or 0

    METODO_LABELS = dict(Pago.METODO_PAGO_CHOICES)

    def _con_metodo(qs):
        return [
            {
                'metodo': m['metodo_pago'],
                'label': METODO_LABELS.get(m['metodo_pago'], m['metodo_pago']),
                'total': m['total'],
                'cantidad': m['cantidad'],
            }
            for m in qs
        ]

    por_concepto = (
        pagos.values('concepto__nombre')
        .annotate(total=Sum('monto'), cantidad=Count('id'))
    )
    por_metodo_pago = _con_metodo(
        pagos.values('metodo_pago')
        .annotate(total=Sum('monto'), cantidad=Count('id'))
    )
    por_metodo_egreso = _con_metodo(
        egresos.values('metodo_pago')
        .annotate(total=Sum('monto'), cantidad=Count('id'))
    )

    sesiones = SesionCaja.objects.filter(
        centro=centro,
        fecha_apertura__date=fecha,
    )

    ctx = _base_ctx(request)
    ctx.update({
        'fecha': fecha,
        'entradas': entradas,
        'salidas': salidas,
        'neto': entradas - salidas,
        'cantidad_pagos': pagos.count(),
        'cantidad_egresos': egresos.count(),
        'por_concepto': por_concepto,
        'por_metodo_pago': por_metodo_pago,
        'por_metodo_egreso': por_metodo_egreso,
        'cajas': Caja.objects.filter(centro=centro),
        'caja_seleccionada': caja_id,
        'sesiones': sesiones,
        'pagos': pagos.select_related('estudiante', 'concepto')[:25],
        'egresos': egresos[:25],
    })

    return render(request, 'caja/reporte_diario.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def historial_sesiones(request):
    centro = get_centro_activo(request)

    sesiones = SesionCaja.objects.filter(
        centro=centro
    ).select_related('caja', 'usuario_apertura', 'usuario_cierre')

    for s in sesiones:
        s.totales = {
            'entradas': s.total_entradas(),
            'salidas': s.total_salidas(),
            'saldo': s.saldo_esperado(),
        }

    ctx = _base_ctx(request)
    ctx['sesiones'] = sesiones
    return render(request, 'caja/historial_sesiones.html', ctx)


@login_required
@centro_required
@role_required(*ROLES_CAJA)
def detalle_sesion(request, sesion_id):
    centro = get_centro_activo(request)

    sesion = get_object_or_404(
        SesionCaja,
        pk=sesion_id,
        centro=centro,
    )

    pagos = sesion.pagos.select_related('estudiante', 'concepto')
    egresos = sesion.egresos.all()

    ctx = _base_ctx(request)
    ctx.update({
        'sesion': sesion,
        'pagos': pagos,
        'egresos': egresos,
        'total_entradas': sesion.total_entradas(),
        'total_salidas': sesion.total_salidas(),
        'efectivo_esperado': sesion.efectivo_esperado(),
    })

    return render(request, 'caja/detalle_sesion.html', ctx)
