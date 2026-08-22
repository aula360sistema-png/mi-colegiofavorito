from collections import Counter
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render

from academico.models import DocenteMateria
from core.decorators import role_required
from core.models import AnioEscolar
from core.utils.centro import obtener_centro_del_usuario
from core.utils.session import get_centro_activo
from docentes.models import AsignacionDocente, Docente
from estudiantes.models import Inscripcion

from .forms import AsistenciaForm, DiaNoDocenciaForm
from .models import AsistenciaEstudiante, DiaNoDocencia
from .services import es_dia_lectivo, registros_del_dia, resumen_por_inscripciones

ROLES_ACCESO = ('docente', 'admin', 'director', 'superadmin', 'secretaria')

AsistenciaFormSet = formset_factory(AsistenciaForm, extra=0)


def _obtener_centro(request):
    """Resuelve el centro del usuario según su rol."""
    if request.user.rol in ('admin', 'superadmin'):
        return get_centro_activo(request)
    return obtener_centro_del_usuario(request)


def _anio_activo(centro):
    return AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()


def _grados_secciones(request, centro, anio):
    """Tuplas (grado_id, grado, seccion_id, seccion) disponibles.

    Para el docente, solo sus grados/secciones asignadas en el año activo.
    Para el resto de roles, todos los grados/secciones con inscripciones.
    """
    pares = set()

    if request.user.rol == 'docente':
        docente = Docente.objects.filter(
            usuario=request.user
        ).first()

        if docente:
            materias = DocenteMateria.objects.filter(
                docente=docente,
                anio_escolar=anio
            ).select_related('grado', 'seccion')

            for dm in materias:
                pares.add((dm.grado_id, dm.grado, dm.seccion_id, dm.seccion))

            asignaciones = AsignacionDocente.objects.filter(
                docente=docente,
                anio_escolar=anio
            ).select_related('grado', 'seccion')

            for ad in asignaciones:
                pares.add((ad.grado_id, ad.grado, ad.seccion_id, ad.seccion))
    else:
        inscripciones = Inscripcion.objects.filter(
            anio_escolar=anio,
            estudiante__estado='activo',
        ).select_related('grado', 'seccion')

        for i in inscripciones:
            pares.add((i.grado_id, i.grado, i.seccion_id, i.seccion))

    return sorted(pares, key=lambda p: (p[1].nombre, p[3].nombre))


def _parsear_fecha(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _inscripciones_de_seccion(anio, grado_id, seccion_id):
    return list(
        Inscripcion.objects.filter(
            anio_escolar=anio,
            grado_id=grado_id,
            seccion_id=seccion_id,
            estudiante__estado='activo',
        ).select_related(
            'estudiante',
            'grado',
            'seccion',
        ).order_by(
            'estudiante__primer_nombre',
            'estudiante__primer_apellido',
        )
    )


# ==========================================
# TOMAR ASISTENCIA
# ==========================================

@login_required
@role_required(*ROLES_ACCESO)
def tomar_asistencia(request):

    centro = _obtener_centro(request)

    if not centro:
        messages.error(request, 'Debe seleccionar un centro educativo.')
        return redirect('core:seleccionar_centro')

    anio = _anio_activo(centro)

    if not anio:
        messages.error(request, 'No hay un año escolar activo.')
        return redirect('core:home')

    grados_secciones = _grados_secciones(request, centro, anio)

    grado_id = request.GET.get('grado') or request.POST.get('grado')
    seccion_id = request.GET.get('seccion') or request.POST.get('seccion')
    fecha_raw = (
        request.GET.get('fecha')
        or request.POST.get('fecha')
        or date.today().isoformat()
    )
    fecha = _parsear_fecha(fecha_raw) or date.today()

    # El pase de lista siempre corresponde al día actual
    if request.user.rol == 'docente':
        fecha = date.today()

    inscripciones = []
    registros = {}
    formset = None
    ya_registrada = False
    es_lectivo = es_dia_lectivo(anio, fecha)
    resumen_dia = None
    filas = []

    if grado_id and seccion_id:
        inscripciones = _inscripciones_de_seccion(
            anio,
            grado_id,
            seccion_id,
        )

        registros = {
            a.inscripcion_id: a.estado
            for a in AsistenciaEstudiante.objects.filter(
                fecha=fecha,
                inscripcion__in=inscripciones,
            )
        }

        ya_registrada = bool(registros)

        if request.method == 'POST':
            formset = AsistenciaFormSet(request.POST)

            if es_lectivo and formset.is_valid():

                for form in formset:

                    data = form.cleaned_data

                    AsistenciaEstudiante.objects.update_or_create(
                        inscripcion_id=data['inscripcion'],
                        fecha=fecha,
                        defaults={
                            'estado': data['estado'],
                            'registrada_por': request.user,
                        },
                    )

                messages.success(
                    request,
                    f'Asistencia registrada para {len(inscripciones)} estudiantes.'
                )

                return redirect(
                    f"{request.path}?grado={grado_id}&seccion={seccion_id}"
                    f"&fecha={fecha.isoformat()}"
                )

            if not es_lectivo:
                messages.error(
                    request,
                    'La fecha seleccionada no es un día lectivo, '
                    'no se puede registrar asistencia.'
                )
                formset = AsistenciaFormSet(
                    initial=[{'inscripcion': i.id} for i in inscripciones]
                )
        else:
            formset = AsistenciaFormSet(
                initial=[
                    {
                        'inscripcion': i.id,
                        'estado': registros.get(i.id, 'presente'),
                    }
                    for i in inscripciones
                ]
            )

        if formset:
            filas = zip(inscripciones, formset.forms)

        if registros:
            conteo = Counter(registros.values())
            resumen_dia = dict(conteo)

    return render(
        request,
        'asistencia/tomar_asistencia.html',
        {
            'anio': anio,
            'grados_secciones': grados_secciones,
            'grado_id': int(grado_id) if grado_id else None,
            'seccion_id': int(seccion_id) if seccion_id else None,
            'fecha': fecha,
            'inscripciones': inscripciones,
            'formset': formset,
            'filas': filas,
            'ya_registrada': ya_registrada,
            'es_lectivo': es_lectivo,
            'resumen_dia': resumen_dia,
            'dia_ayer': (date.today() - timedelta(days=1)).isoformat(),
        }
    )


# ==========================================
# RESUMEN DE ASISTENCIA
# ==========================================

@login_required
@role_required(*ROLES_ACCESO)
def resumen_asistencia(request):

    centro = _obtener_centro(request)

    if not centro:
        messages.error(request, 'Debe seleccionar un centro educativo.')
        return redirect('core:seleccionar_centro')

    anio = _anio_activo(centro)

    if not anio:
        messages.error(request, 'No hay un año escolar activo.')
        return redirect('core:home')

    grados_secciones = _grados_secciones(request, centro, anio)

    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')
    hasta = _parsear_fecha(request.GET.get('hasta')) or date.today()

    resumen = None
    promedio_general = None

    if grado_id and seccion_id:
        inscripciones = _inscripciones_de_seccion(
            anio,
            grado_id,
            seccion_id,
        )

        resumen = resumen_por_inscripciones(
            inscripciones,
            hasta=hasta,
        )

        promedios = [
            r['porcentaje']
            for r in resumen
            if r['porcentaje'] is not None
        ]

        if promedios:
            promedio_general = round(
                sum(promedios) / len(promedios),
                2,
            )

    return render(
        request,
        'asistencia/resumen_asistencia.html',
        {
            'anio': anio,
            'grados_secciones': grados_secciones,
            'grado_id': int(grado_id) if grado_id else None,
            'seccion_id': int(seccion_id) if seccion_id else None,
            'hasta': hasta,
            'resumen': resumen,
            'promedio_general': promedio_general,
        }
    )


# ==========================================
# DIAS DE NO DOCENCIA
# ==========================================

@login_required
@role_required(*ROLES_ACCESO)
def dias_no_docencia(request):

    centro = _obtener_centro(request)

    if not centro:
        messages.error(request, 'Debe seleccionar un centro educativo.')
        return redirect('core:seleccionar_centro')

    anio = _anio_activo(centro)

    if request.method == 'POST':

        if 'eliminar' in request.POST:

            dia_id = request.POST.get('dia_id')

            DiaNoDocencia.objects.filter(
                id=dia_id,
                centro=centro,
            ).delete()

            messages.success(
                request,
                'Día de no docencia eliminado.'
            )

            return redirect('asistencia:dias_no_docencia')

        form = DiaNoDocenciaForm(request.POST, centro=centro)

        if form.is_valid():

            dia = form.save(commit=False)
            dia.centro = centro
            dia.registrado_por = request.user
            dia.save()

            messages.success(
                request,
                'Día de no docencia registrado correctamente.'
            )

            return redirect('asistencia:dias_no_docencia')
    else:

        form = DiaNoDocenciaForm(centro=centro)

    dias = DiaNoDocencia.objects.filter(
        centro=centro,
    ).select_related(
        'anio_escolar',
    ).order_by('-fecha')

    return render(
        request,
        'asistencia/dias_no_docencia.html',
        {
            'form': form,
            'dias': dias,
            'anio': anio,
        }
    )


# ==========================================
# ESTADO DE ASISTENCIA (para recordatorio)
# ==========================================

@login_required
def estado_asistencia(request):
    """Indica si el docente aún no registró la asistencia de hoy.

    Usado por la notificación periódica que recuerda hacer el pase de lista.
    """
    if request.user.rol != 'docente':
        return JsonResponse({'pendiente': False})

    centro = _obtener_centro(request)

    if not centro:
        return JsonResponse({'pendiente': False})

    anio = _anio_activo(centro)

    if not anio:
        return JsonResponse({'pendiente': False})

    hoy = date.today()

    if not es_dia_lectivo(anio, hoy):
        return JsonResponse({'pendiente': False})

    registrados = registros_del_dia(anio, hoy)

    for _gid, _grado, _sid, _seccion in _grados_secciones(request, centro, anio):
        inscripciones = _inscripciones_de_seccion(anio, _gid, _sid)

        if not inscripciones:
            continue

        if not any(ins.id in registrados for ins in inscripciones):
            return JsonResponse({'pendiente': True})

    return JsonResponse({'pendiente': False})


# ==========================================
# ASISTENCIA POR QR
# ==========================================

@login_required
@role_required(*ROLES_ACCESO)
def asistencia_qr_generar(request):
    """Genera códigos QR para los estudiantes de una sección."""
    centro = _obtener_centro(request)
    if not centro:
        messages.error(request, 'Debe seleccionar un centro educativo.')
        return redirect('core:seleccionar_centro')

    anio = _anio_activo(centro)
    if not anio:
        messages.error(request, 'No hay un año escolar activo.')
        return redirect('core:home')

    config = getattr(centro, 'configuracioncentro', None)
    if not config or not config.permitir_qr_asistencia:
        messages.error(
            request, 'El módulo de asistencia por QR no está habilitado.'
        )
        return redirect('asistencia:tomar_asistencia')

    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')

    inscripciones = []
    if grado_id and seccion_id:
        inscripciones = _inscripciones_de_seccion(anio, grado_id, seccion_id)

    grados_secciones = _grados_secciones(request, centro, anio)

    return render(request, 'asistencia/asistencia_qr.html', {
        'anio': anio,
        'grados_secciones': grados_secciones,
        'grado_id': int(grado_id) if grado_id else None,
        'seccion_id': int(seccion_id) if seccion_id else None,
        'inscripciones': inscripciones,
    })


@login_required
def qr_estudiante_data(request, inscripcion_id):
    """Genera el contenido firmado QR para un estudiante."""
    import hashlib
    import hmac
    import json
    import time

    inscripcion = Inscripcion.objects.select_related(
        'estudiante', 'grado', 'seccion'
    ).filter(pk=inscripcion_id).first()

    if not inscripcion:
        return JsonResponse({'error': 'Inscripción no encontrada'}, status=404)

    from django.conf import settings
    secret = settings.SECRET_KEY[:32]

    payload = {
        'i': inscripcion.id,
        'n': inscripcion.estudiante.nombre_completo,
        'm': inscripcion.estudiante.matricula,
        'g': inscripcion.grado.nombre,
        's': inscripcion.seccion.nombre,
        't': int(time.time()),
    }

    payload_json = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        secret.encode(), payload_json.encode(), hashlib.sha256
    ).hexdigest()[:16]

    return JsonResponse({
        'qr_data': f'MCE|{payload_json}|{signature}',
        'estudiante': inscripcion.estudiante.nombre_completo,
        'matricula': inscripcion.estudiante.matricula,
    })


@login_required
@role_required(*ROLES_ACCESO)
def qr_escanear(request):
    """Procesa un escaneo QR y registra asistencia."""
    import json
    import hmac
    import hashlib

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    qr_payload = data.get('qr_data', '')

    if not qr_payload or not qr_payload.startswith('MCE|'):
        return JsonResponse({'error': 'Código QR inválido'}, status=400)

    try:
        _, payload_json, signature = qr_payload.split('|', 2)
    except ValueError:
        return JsonResponse({'error': 'Formato QR inválido'}, status=400)

    from django.conf import settings
    secret = settings.SECRET_KEY[:32]

    expected_sig = hmac.new(
        secret.encode(), payload_json.encode(), hashlib.sha256
    ).hexdigest()[:16]

    if not hmac.compare_digest(signature, expected_sig):
        return JsonResponse({'error': 'Firma QR inválida'}, status=400)

    payload = json.loads(payload_json)
    inscripcion_id = payload.get('i')

    if not inscripcion_id:
        return JsonResponse({'error': 'Datos incompletos en QR'}, status=400)

    centro = _obtener_centro(request)
    anio = _anio_activo(centro) if centro else None

    inscripcion = Inscripcion.objects.select_related(
        'estudiante', 'anio_escolar'
    ).filter(pk=inscripcion_id).first()

    if not inscripcion:
        return JsonResponse({'error': 'Inscripción no encontrada'}, status=404)

    hoy = date.today()

    if anio and not es_dia_lectivo(anio, hoy):
        return JsonResponse({'error': 'Hoy no es día lectivo'}, status=400)

    asistencia, created = AsistenciaEstudiante.objects.update_or_create(
        inscripcion_id=inscripcion_id,
        fecha=hoy,
        defaults={
            'estado': 'presente',
            'registrada_por': request.user,
        },
    )

    estado = 'registrada' if created else 'actualizada'

    return JsonResponse({
        'success': True,
        'mensaje': (
            f'Asistencia {estado} para '
            f'{inscripcion.estudiante.nombre_completo}'
        ),
        'estudiante': inscripcion.estudiante.nombre_completo,
        'estado': asistencia.estado,
        'fecha': hoy.isoformat(),
    })


# ==========================================
# ASISTENCIA POR BIOMETRICO
# ==========================================

@login_required
@role_required(*ROLES_ACCESO)
def asistencia_biometrico(request):
    """Panel de asistencia biométrica.

    Preparado para integración con dispositivos biométricos
    (ZKTeco, Suprema, etc.). Funciona como simulador que permite
    marcar asistencia por código de estudiante (matrícula).
    """
    centro = _obtener_centro(request)
    if not centro:
        messages.error(request, 'Debe seleccionar un centro educativo.')
        return redirect('core:seleccionar_centro')

    anio = _anio_activo(centro)
    if not anio:
        messages.error(request, 'No hay un año escolar activo.')
        return redirect('core:home')

    config = getattr(centro, 'configuracioncentro', None)
    if not config or not config.usar_biometrico:
        messages.error(
            request, 'El módulo biométrico no está habilitado.'
        )
        return redirect('asistencia:tomar_asistencia')

    hoy = date.today()

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        if codigo:
            inscripcion = Inscripcion.objects.filter(
                anio_escolar=anio,
                estudiante__matricula=codigo,
                estudiante__estado='activo',
            ).select_related('estudiante').first()

            if inscripcion:
                if es_dia_lectivo(anio, hoy):
                    asistencia, created = (
                        AsistenciaEstudiante.objects.update_or_create(
                            inscripcion=inscripcion,
                            fecha=hoy,
                            defaults={
                                'estado': 'presente',
                                'registrada_por': request.user,
                            },
                        )
                    )
                    msg = (
                        f'Asistencia '
                        f'{"registrada" if created else "actualizada"} '
                        f'para {inscripcion.estudiante.nombre_completo}'
                    )
                    messages.success(request, msg)
                else:
                    messages.error(request, 'Hoy no es día lectivo.')
            else:
                messages.error(
                    request,
                    f'No se encontró estudiante con código: {codigo}',
                )

    ultimas_asistencias = AsistenciaEstudiante.objects.filter(
        fecha=hoy,
        inscripcion__anio_escolar=anio,
    ).select_related(
        'inscripcion__estudiante',
        'registrada_por',
    ).order_by('-created_at')[:20]

    return render(request, 'asistencia/asistencia_biometrico.html', {
        'anio': anio,
        'hoy': hoy,
        'ultimas_asistencias': ultimas_asistencias,
    })


@login_required
@role_required(*ROLES_ACCESO)
def asistencia_biometrico_api(request):
    """API endpoint para dispositivos biométricos externos.

    POST con JSON: {"matricula": "00123"}
    Registra asistencia y retorna resultado.
    """
    import json

    if request.method != 'POST':
        return JsonResponse(
            {'error': 'Método no permitido'}, status=405
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    matricula = data.get('matricula', '').strip()
    if not matricula:
        return JsonResponse({'error': 'Matrícula requerida'}, status=400)

    centro = _obtener_centro(request)
    anio = _anio_activo(centro) if centro else None

    if not anio:
        return JsonResponse(
            {'error': 'No hay año escolar activo'}, status=400
        )

    hoy = date.today()

    if not es_dia_lectivo(anio, hoy):
        return JsonResponse({'error': 'No es día lectivo'}, status=400)

    inscripcion = Inscripcion.objects.filter(
        anio_escolar=anio,
        estudiante__matricula=matricula,
        estudiante__estado='activo',
    ).select_related('estudiante').first()

    if not inscripcion:
        return JsonResponse(
            {'error': 'Estudiante no encontrado'}, status=404
        )

    asistencia, created = AsistenciaEstudiante.objects.update_or_create(
        inscripcion=inscripcion,
        fecha=hoy,
        defaults={
            'estado': 'presente',
            'registrada_por': request.user,
        },
    )

    return JsonResponse({
        'success': True,
        'estudiante': inscripcion.estudiante.nombre_completo,
        'matricula': matricula,
        'estado': asistencia.estado,
        'registrada': created,
        'fecha': hoy.isoformat(),
    })
