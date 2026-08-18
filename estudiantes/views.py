from django.shortcuts import render
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

from academico.models import Grado, Seccion
from django.contrib.auth.decorators import login_required
# Create your views here.
from django.shortcuts import render, redirect

from academico.models import DocenteMateria
from core.decorators import centro_required, role_required
from .models import Estudiante
from usuarios.models import Usuario
from core.models import CentroEducativo


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Estudiante, Inscripcion
from .forms import EstudianteForm
from core.models import CentroEducativo

from core.models import AnioEscolar
from core.models import ConfiguracionCentro
from django.contrib import messages
from .forms import InscripcionAvanzadaForm


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string
from usuarios.models import Usuario
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch

from core.utils.session import get_centro_activo
from .utils import validar_promocion_estudiante
from core.utils.anio import obtener_anio_activo
from caja.services import deuda_detalle_estudiante, tiene_deuda_pendiente
from django.utils import timezone
from .forms import DisciplinaForm, ObservacionEstudianteForm
from .models import (
    HistorialClinicoEstudiante,
    ObservacionEstudiante,
    RegistroSalud,
    SolicitudCertificado,
)
from .forms import (
    HistorialClinicoForm,
    RegistroSaludForm,
    SolicitudCertificadoForm,
    SolicitudCobroForm,
    SolicitudRechazoForm,
)
from .services.kardex import construir_kardex, construir_record_notas
from .services.pagos import procesar_pago_online, reembolsar_pago_online
from .services.listados import (
    estudiantes_del_centro,
    observaciones_del_centro,
    solicitudes_del_centro,
)
from academico.services import estructura


@login_required
def estudiante_inicio(request):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user
    )

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

    return render(request, 'estudiantes/estudiante_inicio.html', {
        'estudiante': estudiante,
        'kardex': kardex,
        'inscripcion_actual': inscripcion_actual,
        'anio_actual': anio_actual,
        'total_anios': len(kardex['anios']),
    })


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estudiante_create(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('core:seleccionar_centro')

    if request.method == 'POST':

        form = EstudianteForm(request.POST, request.FILES, centro=centro)

        if form.is_valid():

            estudiante = form.save(commit=False)
            estudiante.centro = centro

            password = get_random_string(8)

            usuario = Usuario.objects.create_user(
                username=estudiante.matricula,
                email=f"{estudiante.matricula}@colegio.com",
                password=password
            )

            usuario.rol = 'estudiante'
            usuario.debe_cambiar_password = True
            usuario.save()

            estudiante.usuario = usuario
            estudiante.save()

            return render(
                request,
                'usuarios/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password,
                    'centro': centro.nombre,
                    'tipo_nombre': 'Estudiante',
                    'tipo_slug': 'estudiante',
                }
            )

    else:
        form = EstudianteForm(centro=centro)

    return render(
        request,
        'estudiantes/estudiante_form.html',
        {
            'form': form,
            'estudiante': None
        }
    )


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estudiante_update(request, pk):

    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':

        form = EstudianteForm(
            request.POST,
            request.FILES,
            instance=estudiante,
            centro=centro
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Estudiante actualizado correctamente."
            )

            return redirect(
                'estudiante_detail',
                pk=estudiante.pk
            )

    else:

        form = EstudianteForm(
            instance=estudiante,
            centro=centro
        )

    return render(
        request,
        'estudiantes/estudiante_form.html',
        {
            'form': form,
            'estudiante': estudiante
        }
    )

@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estudiante_detail(request, pk):

    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    inscripciones = (
        Inscripcion.objects
        .filter(estudiante=estudiante)
        .select_related(
            'grado',
            'seccion',
            'anio_escolar'
        )
        .order_by('-anio_escolar__fecha_inicio')
    )

    inscripcion_actual = inscripciones.filter(
        anio_escolar__activo=True
    ).first()

    kardex = construir_kardex(estudiante, centro)

    promedio_actual = None
    asistencia_actual = None

    if inscripcion_actual:
        if inscripcion_actual.promedio_final is not None:
            promedio_actual = float(inscripcion_actual.promedio_final)

        for y in kardex['anios']:
            if y['anio'].id == inscripcion_actual.anio_escolar_id:
                if promedio_actual is None:
                    promedio_actual = y['promedio_general']
                asistencia_actual = y['asistencia']
                break

    context = {
        'estudiante': estudiante,
        'inscripciones': inscripciones,
        'inscripcion_actual': inscripcion_actual,
        'kardex': kardex,
        'observacion_form': ObservacionEstudianteForm(centro=centro),
        'promedio_actual': promedio_actual,
        'asistencia_actual': asistencia_actual,
        'total_anios': len(kardex['anios']),
        'iniciales': (
            f"{(estudiante.primer_nombre or '')[0:1]}"
            f"{(estudiante.primer_apellido or '')[0:1]}"
        ).upper(),
    }

    return render(
        request,
        'estudiantes/estudiante_detail.html',
        context
    )
@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estudiante_delete(request, pk):
    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        estudiante.delete()
        return redirect('estudiante_list')

    return render(
        request,
        'estudiantes/estudiante_confirm_delete.html',
        {'estudiante': estudiante}
    )

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estudiante_list(request):

    centro = request.centro

    q = request.GET.get("q", "").strip()

    anio_activo = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

    from .services.listados import estudiantes_del_centro
    estudiantes = estudiantes_del_centro(centro, anio_activo)

    if q:
        q = q.lower()
        estudiantes = [
            e for e in estudiantes
            if q in (e.matricula or '').lower()
            or q in (e.primer_nombre or '').lower()
            or q in (e.segundo_nombre or '').lower()
            or q in (e.primer_apellido or '').lower()
            or q in (e.segundo_apellido or '').lower()
        ]

    lista = list(estudiantes)
    total = len(lista)
    matriculados = sum(1 for e in lista if getattr(e, 'inscripcion_actual', None))
    sin_matricula = total - matriculados

    estado = request.GET.get("estado", "")

    if estado == "matriculado":
        lista = [e for e in lista if getattr(e, 'inscripcion_actual', None)]
    elif estado == "sin_matricula":
        lista = [e for e in lista if not getattr(e, 'inscripcion_actual', None)]

    return render(
        request,
        'estudiantes/estudiante_list.html',
        {
            'estudiantes': lista,
            'centro': centro,
            'anio_activo': anio_activo,
            'q': q,
            'estado': estado,
            'stats': {
                'total': total,
                'matriculados': matriculados,
                'sin_matricula': sin_matricula,
            },
        }
    )


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def ajax_cargar_secciones(request):
    grado_id = request.GET.get('grado')

    secciones = Seccion.objects.filter(
        grados__id=grado_id
    ).values('id', 'nombre')

    return JsonResponse(list(secciones), safe=False)


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AnioEscolar
from core.utils.session import get_centro_activo

from .forms import InscripcionAvanzadaForm
from .models import Estudiante, Inscripcion
from .utils import validar_promocion_estudiante


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def inscribir_estudiante_avanzado(request, estudiante_id):

 

    # ======================================
    # CENTRO ACTIVO
    # ======================================

    centro = get_centro_activo(request)

    if not centro:
        messages.error(
            request,
            'Debe seleccionar un centro educativo.'
        )
        return redirect('core:seleccionar_centro')

    # ======================================
    # ESTUDIANTE
    # ======================================

    estudiante = get_object_or_404(
        Estudiante,
        id=estudiante_id,
        centro=centro
    )

    # ======================================
    # AÑO ESCOLAR ACTIVO
    # ======================================

    try:

        anio_escolar = AnioEscolar.objects.get(
            centro=centro,
            activo=True
        )

    except AnioEscolar.DoesNotExist:

        messages.error(
            request,
            'No existe un año escolar activo.'
        )

        return redirect(
            'estudiante_detail',
            pk=estudiante.id
        )

    # ======================================
    # VALIDAR PROMOCIÓN
    # ======================================

    resultado = validar_promocion_estudiante(
        estudiante,
        anio_escolar
    )

    if not resultado['permitido']:

        messages.error(
            request,
            resultado['mensaje']
        )

        return redirect(
            'estudiante_detail',
            pk=estudiante.id
        )

    if resultado['mensaje']:

        messages.info(
            request,
            resultado['mensaje']
        )

    # ======================================
    # VALIDAR DOBLE INSCRIPCIÓN
    # ======================================

    ya_inscrito = Inscripcion.objects.filter(
        estudiante=estudiante,
        anio_escolar=anio_escolar
    ).exists()

    if ya_inscrito:

        messages.warning(
            request,
            'Este estudiante ya está inscrito en el año escolar activo.'
        )

        return redirect(
            'estudiante_detail',
            pk=estudiante.id
        )

    # ======================================
    # POST
    # ======================================

    if request.method == 'POST':

        form = InscripcionAvanzadaForm(
            request.POST,
            centro=centro
        )

        if form.is_valid():

            inscripcion = form.save(commit=False)

            # ==================================
            # VALIDAR GRADO PERMITIDO
            # ==================================

            grado_permitido = resultado.get(
                'grado_permitido'
            )

            if grado_permitido:

                if inscripcion.grado != grado_permitido:

                    messages.error(
                        request,
                        (
                            f'El estudiante solamente puede '
                            f'inscribirse en '
                            f'{grado_permitido}.'
                        )
                    )

                    return redirect(
                        'inscribir_estudiante',
                        estudiante_id=estudiante.id
                    )

            inscripcion.estudiante = estudiante
            inscripcion.centro = centro
            inscripcion.anio_escolar = anio_escolar

            inscripcion.save()

            logger.debug(
                "Inscripción guardada: %s",
                inscripcion.id
            )

            messages.success(
                request,
                'Estudiante inscrito correctamente.'
            )

            return redirect(
                'estudiante_detail',
                pk=estudiante.id
            )

        logger.warning("Errores del formulario: %s", form.errors)

    else:

        form = InscripcionAvanzadaForm(
            centro=centro
        )

    # ======================================
    # RENDER
    # ======================================
    inscripcion_actual = Inscripcion.objects.filter(
        estudiante=estudiante,
        anio_escolar=anio_escolar
    ).first()

    return render(
        request,
        'estudiantes/inscripcion_avanzada_form.html',
        {
            'form': form,
            'estudiante': estudiante,
            'anio_escolar': anio_escolar,
            'resultado_promocion': resultado,
            'inscripcion_actual' : inscripcion_actual

        }
    )



@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def inscripcion_asignaturas(request, inscripcion_id):

    centro = get_centro_activo(request)

    if not centro:
        return redirect('core:seleccionar_centro')

    inscripcion = get_object_or_404(
        Inscripcion,
        id=inscripcion_id,
        centro=centro
    )

    asignaciones = (
        DocenteMateria.objects
        .filter(
            grado=inscripcion.grado,
            seccion=inscripcion.seccion,
            anio_escolar=inscripcion.anio_escolar
        )
        .select_related(
            'asignatura',
            'docente'
        )
        .order_by('asignatura__nombre')
    )

    return render(
        request,
        'estudiantes/inscripcion_asignaturas.html',
        {
            'inscripcion': inscripcion,
            'asignaciones': asignaciones,
            'total_materias': asignaciones.count()
        }
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def historial_estudiantes(request):

    centro = get_centro_activo(request)

    if not centro:
        messages.error(
            request,
            'Debe seleccionar un centro educativo.'
        )
        return redirect('core:seleccionar_centro')

    q = request.GET.get('q', '').strip()
    anio_id = request.GET.get('anio', '').strip()
    grado_id = request.GET.get('grado', '').strip()
    seccion_id = request.GET.get('seccion', '').strip()
    estado = request.GET.get('estado', '').strip()

    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')

    grados = Grado.objects.filter(
        nivel__centro=centro
    ).order_by('nombre')

    secciones = Seccion.objects.filter(
        centro=centro
    ).order_by('nombre')

    from .services.listados import inscripciones_del_centro
    inscripciones = inscripciones_del_centro(centro)

    if q:
        q = q.lower()
        inscripciones = [
            i for i in inscripciones
            if q in (i.estudiante.primer_nombre or '').lower()
            or q in (i.estudiante.primer_apellido or '').lower()
            or q in (i.estudiante.matricula or '').lower()
        ]

    if anio_id:
        inscripciones = [
            i for i in inscripciones
            if str(i.anio_escolar_id) == str(anio_id)
        ]

    if grado_id:
        inscripciones = [
            i for i in inscripciones
            if str(i.grado_id or '') == str(grado_id)
        ]

    if seccion_id:
        inscripciones = [
            i for i in inscripciones
            if str(i.seccion_id or '') == str(seccion_id)
        ]

    if estado:
        inscripciones = [
            i for i in inscripciones if i.estado_final == estado
        ]

    total_registros = len(inscripciones)

    resumen = {
        'aprobados': sum(1 for i in inscripciones if i.estado_final == 'aprobado'),
        'recuperacion': sum(1 for i in inscripciones if i.estado_final == 'recuperacion'),
        'reprobados': sum(1 for i in inscripciones if i.estado_final == 'reprobado'),
        'pendientes': sum(
            1 for i in inscripciones
            if i.estado_final in ('pendiente', 'sin_calificacion')
        ),
    }

    paginator = Paginator(inscripciones, 10)

    try:
        page_obj = paginator.get_page(request.GET.get('page'))
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    context = {
        'centro': centro,
        'inscripciones': page_obj.object_list,
        'page_obj': page_obj,

        'anios': anios,
        'grados': grados,
        'secciones': secciones,

        'q': q,
        'estado': estado,

        'anio_seleccionado': anio_id,
        'grado_seleccionado': grado_id,
        'seccion_seleccionada': seccion_id,

        'total_registros': total_registros,
        'resumen': resumen,
    }

    return render(
        request,
        'estudiantes/historial_estudiantes.html',
        context
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def constancias(request):
    centro = get_centro_activo(request)

    anio_actual = obtener_anio_activo(centro)

    q = request.GET.get('q', '').strip()

    estudiantes = estudiantes_del_centro(centro, anio_actual)

    if q:
        ql = q.lower()
        estudiantes = [
            e for e in estudiantes
            if ql in (e.matricula or '').lower()
            or ql in (e.primer_nombre or '').lower()
            or ql in (e.primer_apellido or '').lower()
        ]

    lista = []
    for e in estudiantes:
        inscripcion = (getattr(e, 'inscripcion_actual', None) or [None])[0]
        e.constancia_grado = inscripcion.grado if inscripcion else None
        e.constancia_seccion = inscripcion.seccion if inscripcion else None
        e.constancia_deuda = deuda_detalle_estudiante(centro, e, anio_actual)
        lista.append(e)

    total = len(lista)
    matriculados = sum(1 for e in lista if e.constancia_grado)
    sin_matricula = total - matriculados

    paginator = Paginator(lista, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'estudiantes/constancias.html', {
        'centro': centro,
        'anio_actual': anio_actual,
        'estudiantes': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': {
            'total': total,
            'matriculados': matriculados,
            'sin_matricula': sin_matricula,
        },
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def constancia_estudiante(request, pk):
    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    anio_actual = obtener_anio_activo(centro)

    if tiene_deuda_pendiente(centro, estudiante, anio_actual):
        messages.error(
            request,
            (
                f"No se puede emitir la constancia: "
                f"{estudiante.nombre_completo()} tiene deuda pendiente."
            )
        )
        return redirect('constancias')

    inscripcion = (
        Inscripcion.objects
        .filter(
            estudiante=estudiante,
            centro=centro,
            anio_escolar=anio_actual
        )
        .select_related('grado', 'seccion')
        .first()
    )

    return render(request, 'estudiantes/constancia_imprimir.html', {
        'centro': centro,
        'estudiante': estudiante,
        'anio_actual': anio_actual,
        'inscripcion': inscripcion,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def cambiar_estado_estudiante(request, pk):
    """
    Flujo de retiro/traslado/egreso: actualiza el estado del estudiante
    y, si es retirado, marca la matrícula del año activo como retirada.
    """

    if request.method != 'POST':
        return redirect('estudiante_detail', pk=pk)

    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    estado = request.POST.get('estado')

    estados_validos = ['activo', 'retirado', 'egresado']

    if estado not in estados_validos:
        messages.error(request, "Estado inválido.")
        return redirect('estudiante_detail', pk=pk)

    estudiante.estado = estado
    estudiante.save()

    if estado == 'retirado':
        Inscripcion.objects.filter(
            estudiante=estudiante,
            centro=centro,
            anio_escolar__activo=True
        ).update(estado_final='retirado', fecha_cierre=timezone.now().date())

    messages.success(
        request,
        f"Estado del estudiante actualizado a "
        f"{estudiante.get_estado_display().lower()}."
    )

    return redirect('estudiante_detail', pk=pk)


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def kardex_imprimir(request, pk):
    centro = request.centro

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    record = construir_record_notas(estudiante, centro)

    inscripcion_actual = Inscripcion.objects.filter(
        estudiante=estudiante,
        centro=centro,
        anio_escolar__activo=True,
    ).select_related('grado', 'seccion', 'anio_escolar').first()

    quien_suscribe = (
        request.user.get_full_name().strip()
        or request.user.username
    )

    return render(
        request,
        'estudiantes/kardex_imprimir.html',
        {
            'record': record,
            'estudiante': estudiante,
            'centro': centro,
            'inscripcion_actual': inscripcion_actual,
            'quien_suscribe': quien_suscribe,
        }
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def agregar_observacion_estudiante(request, pk):
    centro = request.centro

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = ObservacionEstudianteForm(
            request.POST,
            centro=centro
        )

        if form.is_valid():
            observacion = form.save(commit=False)
            observacion.estudiante = estudiante
            observacion.save()

            messages.success(
                request,
                'Observación registrada correctamente.'
            )

        else:
            messages.error(
                request,
                'No se pudo registrar la observación.'
            )

    return redirect('estudiante_detail', pk=pk)


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def disciplina(request):
    centro = get_centro_activo(request)

    if not centro:
        messages.error(
            request,
            'Debe seleccionar un centro educativo.'
        )
        return redirect('core:seleccionar_centro')

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    anio_id = request.GET.get('anio', '').strip()
    grado_id = request.GET.get('grado', '').strip()
    seccion_id = request.GET.get('seccion', '').strip()
    estudiante_id = request.GET.get('estudiante', '').strip()

    anios = estructura.anios_escolares(centro)

    grados = estructura.grados(centro)

    secciones = estructura.secciones(centro)

    observaciones = observaciones_del_centro(centro)

    if q:
        ql = q.lower()
        observaciones = [
            o for o in observaciones
            if ql in (o.estudiante.primer_nombre or '').lower()
            or ql in (o.estudiante.primer_apellido or '').lower()
            or ql in (o.estudiante.matricula or '').lower()
        ]

    if tipo:
        observaciones = [o for o in observaciones if o.tipo == tipo]

    if anio_id:
        try:
            anio_int = int(anio_id)
        except (ValueError, TypeError):
            anio_int = None
        if anio_int is not None:
            observaciones = [
                o for o in observaciones if o.anio_escolar_id == anio_int
            ]

    if grado_id:
        try:
            grado_int = int(grado_id)
        except (ValueError, TypeError):
            grado_int = None
        if grado_int is not None:
            observaciones = [
                o for o in observaciones
                if any(
                    i.grado_id == grado_int
                    for i in getattr(o.estudiante, 'inscripciones_centro', [])
                )
            ]

    if seccion_id:
        try:
            seccion_int = int(seccion_id)
        except (ValueError, TypeError):
            seccion_int = None
        if seccion_int is not None:
            observaciones = [
                o for o in observaciones
                if any(
                    i.seccion_id == seccion_int
                    for i in getattr(o.estudiante, 'inscripciones_centro', [])
                )
            ]

    estudiante_filtro = None

    if estudiante_id:
        try:
            estudiante_int = int(estudiante_id)
        except (ValueError, TypeError):
            estudiante_int = None
        if estudiante_int is not None:
            estudiante_filtro = Estudiante.objects.filter(
                pk=estudiante_int,
                centro=centro
            ).first()
            if estudiante_filtro:
                observaciones = [
                    o for o in observaciones
                    if o.estudiante_id == estudiante_int
                ]

    observaciones = sorted(
        observaciones,
        key=lambda o: o.estudiante.primer_apellido or ''
    )
    observaciones = sorted(
        observaciones,
        key=lambda o: o.fecha,
        reverse=True,
    )

    total_registros = len(observaciones)

    resumen = {
        'observacion': sum(1 for o in observaciones if o.tipo == 'observacion'),
        'conducta': sum(1 for o in observaciones if o.tipo == 'conducta'),
        'merito': sum(1 for o in observaciones if o.tipo == 'merito'),
        'amonestacion': sum(1 for o in observaciones if o.tipo == 'amonestacion'),
    }

    paginator = Paginator(observaciones, 15)

    try:
        page_obj = paginator.get_page(request.GET.get('page'))
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    context = {
        'centro': centro,
        'observaciones': page_obj.object_list,
        'page_obj': page_obj,

        'anios': anios,
        'grados': grados,
        'secciones': secciones,

        'q': q,
        'tipo': tipo,

        'anio_seleccionado': anio_id,
        'grado_seleccionado': grado_id,
        'seccion_seleccionada': seccion_id,

        'estudiante_filtro': estudiante_filtro,

        'total_registros': total_registros,
        'resumen': resumen,

        'disciplina_form': DisciplinaForm(
            centro=centro,
            initial={'estudiante': estudiante_filtro.pk} if estudiante_filtro else None,
        ),
    }

    return render(
        request,
        'estudiantes/disciplina.html',
        context
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def disciplina_registrar(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = DisciplinaForm(
            request.POST,
            centro=centro
        )

        if form.is_valid():
            observacion = form.save()

            messages.success(
                request,
                (
                    f"{observacion.get_tipo_display()} registrada para "
                    f"{observacion.estudiante.nombre_completo()}."
                )
            )
        else:
            messages.error(
                request,
                'No se pudo registrar. Verifique los datos.'
            )

    return redirect('disciplina')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def disciplina_eliminar(request, pk):
    centro = get_centro_activo(request)

    observacion = get_object_or_404(
        ObservacionEstudiante,
        pk=pk,
        estudiante__centro=centro
    )

    if request.method == 'POST':
        observacion.delete()
        messages.success(
            request,
            'Registro de disciplina eliminado.'
        )

    return redirect('disciplina')


# ============================================================
# SOLICITUDES DE CERTIFICADOS (Portal estudiante)
# ============================================================

@login_required
def estudiante_solicitudes(request):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user
    )

    solicitudes = (
        SolicitudCertificado.objects
        .filter(estudiante=estudiante)
        .order_by('-created_at')
    )

    config = ConfiguracionCentro.objects.filter(
        centro=estudiante.centro
    ).first()

    if request.method == 'POST':
        form = SolicitudCertificadoForm(request.POST)

        if form.is_valid():
            if config and not config.modulo_certificados:
                messages.error(
                    request,
                    'El centro no tiene habilitadas las solicitudes de certificados.'
                )
            elif tiene_deuda_pendiente(estudiante.centro, estudiante):
                messages.error(
                    request,
                    (
                        'No puedes solicitar certificados mientras tengas '
                        'deuda pendiente con el centro.'
                    )
                )
            else:
                solicitud = form.save(commit=False)
                solicitud.estudiante = estudiante
                solicitud.solicitante = request.user
                solicitud.monto = config.precio_certificado if config else 0
                solicitud.save()

                messages.success(
                    request,
                    (
                        f"Solicitud {solicitud.folio} registrada. "
                        f"Estado: {solicitud.get_estado_display()}."
                    )
                )
                return redirect('estudiante_solicitudes')
    else:
        form = SolicitudCertificadoForm()

    return render(
        request,
        'estudiantes/estudiante_solicitudes.html',
        {
            'estudiante': estudiante,
            'solicitudes': solicitudes,
            'form': form,
            'config': config,
            'modulo_activo': bool(config and config.modulo_certificados),
        }
    )


# ============================================================
# HISTORIAL CLÍNICO / EMERGENCIA
# ============================================================

@login_required
def estudiante_historial_clinico(request):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user
    )

    historial, _ = HistorialClinicoEstudiante.objects.get_or_create(
        estudiante=estudiante
    )

    registros = estudiante.registros_salud.all()

    return render(
        request,
        'estudiantes/estudiante_historial.html',
        {
            'estudiante': estudiante,
            'historial': historial,
            'registros': registros,
        }
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def historial_clinico_list(request):
    centro = request.centro

    q = request.GET.get('q', '').strip()
    grado_id = request.GET.get('grado', '')
    seccion_id = request.GET.get('seccion', '')

    estudiantes = Estudiante.objects.filter(
        centro=centro
    ).select_related('usuario').prefetch_related(
        'historial_clinico'
    )

    if q:
        estudiantes = estudiantes.filter(
            Q(matricula__icontains=q) |
            Q(primer_nombre__icontains=q) |
            Q(segundo_nombre__icontains=q) |
            Q(primer_apellido__icontains=q) |
            Q(segundo_apellido__icontains=q)
        )

    if grado_id:
        estudiantes = estudiantes.filter(
            inscripcion__grado_id=grado_id
        )

    if seccion_id:
        estudiantes = estudiantes.filter(
            inscripcion__seccion_id=seccion_id
        )

    estudiantes = estudiantes.distinct().order_by(
        'primer_apellido', 'primer_nombre'
    )

    paginator = Paginator(estudiantes, 15)

    try:
        page_obj = paginator.get_page(request.GET.get('page'))
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    grados = Grado.objects.filter(nivel__centro=centro)
    secciones = Seccion.objects.filter(grados__nivel__centro=centro).distinct()

    context = {
        'estudiantes': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'grados': grados,
        'secciones': secciones,
        'grado_seleccionado': grado_id,
        'seccion_seleccionada': seccion_id,
        'con_historial': HistorialClinicoEstudiante.objects.filter(
            estudiante__centro=centro
        ).count(),
    }

    return render(
        request,
        'estudiantes/historial_clinico_list.html',
        context
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def historial_clinico_detalle(request, pk):
    centro = request.centro

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    historial, _ = HistorialClinicoEstudiante.objects.get_or_create(
        estudiante=estudiante
    )

    registros = estudiante.registros_salud.select_related(
        'registrado_por'
    ).order_by('-fecha', '-created_at')

    return render(
        request,
        'estudiantes/historial_clinico_detalle.html',
        {
            'estudiante': estudiante,
            'historial': historial,
            'registros': registros,
            'form_tipo_opciones': RegistroSalud.TIPOS,
        }
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def historial_clinico_editar(request, pk):
    centro = request.centro

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    historial, _ = HistorialClinicoEstudiante.objects.get_or_create(
        estudiante=estudiante
    )

    if request.method == 'POST':
        form = HistorialClinicoForm(
            request.POST,
            instance=historial,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Historial clínico de {estudiante.nombre_completo()} actualizado."
            )
            return redirect('historial_clinico_detalle', pk=estudiante.pk)
    else:
        form = HistorialClinicoForm(instance=historial)

    return render(
        request,
        'estudiantes/historial_clinico_form.html',
        {
            'form': form,
            'estudiante': estudiante,
            'historial': historial,
        }
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def registro_salud_crear(request, pk):
    centro = request.centro

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = RegistroSaludForm(request.POST)

        if form.is_valid():
            registro = form.save(commit=False)
            registro.estudiante = estudiante
            registro.registrado_por = request.user
            registro.save()
            messages.success(
                request,
                'Registro de salud agregado correctamente.'
            )
        else:
            messages.error(
                request,
                'No se pudo registrar. Verifique los datos.'
            )

    return redirect('historial_clinico_detalle', pk=estudiante.pk)


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def registro_salud_eliminar(request, pk):
    centro = request.centro

    registro = get_object_or_404(
        RegistroSalud,
        pk=pk,
        estudiante__centro=centro
    )

    if request.method == 'POST':
        registro.delete()
        messages.success(request, 'Registro de salud eliminado.')

    return redirect(
        'historial_clinico_detalle',
        pk=registro.estudiante_id
    )


@login_required
def estudiante_solicitud_pagar(request, pk):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user
    )

    solicitud = get_object_or_404(
        SolicitudCertificado,
        pk=pk,
        estudiante=estudiante
    )

    if solicitud.estado != 'pendiente':
        messages.warning(
            request,
            'Esta solicitud ya no admite pago en línea.'
        )
        return redirect('estudiante_solicitudes')

    referencia, error = procesar_pago_online(solicitud)

    if error:
        messages.error(request, error)
    else:
        messages.success(
            request,
            (
                f"Pago procesado. Referencia: {referencia}. "
                f"La solicitud {solicitud.folio} quedó en estado pagada."
            )
        )

    return redirect('estudiante_solicitudes')


# ============================================================
# PANEL ADMIN DE SOLICITUDES DE CERTIFICADOS
# ============================================================

ESTADOS_CERTIFICADO = SolicitudCertificado.ESTADOS
TIPOS_CERTIFICADO = SolicitudCertificado.TIPOS_CERTIFICADO


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitudes_certificados_list(request):
    centro = request.centro

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()

    solicitudes = solicitudes_del_centro(centro)

    totales = {}
    for s in solicitudes:
        totales[s.estado] = totales.get(s.estado, 0) + 1

    if q:
        ql = q.lower()
        solicitudes = [
            s for s in solicitudes
            if ql in s.folio.lower()
            or ql in s.estudiante.nombre_completo().lower()
            or ql in s.estudiante.matricula.lower()
        ]

    if estado:
        solicitudes = [s for s in solicitudes if s.estado == estado]

    if tipo:
        solicitudes = [s for s in solicitudes if s.tipo_certificado == tipo]

    paginator = Paginator(solicitudes, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'estudiantes/solicitudes_certificados.html',
        {
            'centro': centro,
            'solicitudes': page_obj.object_list,
            'page_obj': page_obj,
            'q': q,
            'estado': estado,
            'tipo': tipo,
            'estados': ESTADOS_CERTIFICADO,
            'tipos': TIPOS_CERTIFICADO,
            'totales': totales,
            'form_rechazo': SolicitudRechazoForm(),
            'form_cobro': SolicitudCobroForm(),
        }
    )


def _solicitud_del_centro(centro, pk):
    return get_object_or_404(
        SolicitudCertificado,
        pk=pk,
        estudiante__centro=centro
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitud_aprobar(request, pk):
    centro = request.centro
    solicitud = _solicitud_del_centro(centro, pk)

    if request.method != 'POST':
        return redirect('solicitudes_certificados')

    if solicitud.estado != 'pendiente':
        messages.warning(
            request,
            f"La solicitud {solicitud.folio} ya no está pendiente."
        )
        return redirect('solicitudes_certificados')

    if tiene_deuda_pendiente(
        centro,
        solicitud.estudiante,
        obtener_anio_activo(centro),
    ):
        messages.error(
            request,
            (
                f"No se puede aprobar {solicitud.folio}: "
                f"{solicitud.estudiante.nombre_completo()} "
                "tiene deuda pendiente."
            )
        )
        return redirect('solicitudes_certificados')

    solicitud.estado = 'aprobada'
    solicitud.aprobado_por = request.user
    solicitud.aprobado_en = timezone.now()
    solicitud.save()

    messages.success(
        request,
        f"Solicitud {solicitud.folio} aprobada."
    )
    return redirect('solicitudes_certificados')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitud_rechazar(request, pk):
    centro = request.centro
    solicitud = _solicitud_del_centro(centro, pk)

    if request.method != 'POST':
        return redirect('solicitudes_certificados')

    if solicitud.estado != 'pendiente':
        messages.warning(
            request,
            f"La solicitud {solicitud.folio} ya no está pendiente."
        )
        return redirect('solicitudes_certificados')

    form = SolicitudRechazoForm(request.POST)
    if form.is_valid():
        solicitud.estado = 'rechazada'
        solicitud.rechazo_motivo = form.cleaned_data['rechazo_motivo']
        solicitud.save()
        messages.success(
            request,
            f"Solicitud {solicitud.folio} rechazada."
        )
    else:
        messages.error(
            request,
            'Debe indicar el motivo del rechazo.'
        )

    return redirect('solicitudes_certificados')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitud_cobrar(request, pk):
    centro = request.centro
    solicitud = _solicitud_del_centro(centro, pk)

    if request.method != 'POST':
        return redirect('solicitudes_certificados')

    if solicitud.estado != 'aprobada':
        messages.warning(
            request,
            (
                f"La solicitud {solicitud.folio} debe estar aprobada "
                f"para registrar el cobro en caja."
            )
        )
        return redirect('solicitudes_certificados')

    form = SolicitudCobroForm(request.POST)
    if form.is_valid():
        solicitud.pagado = True
        solicitud.pagado_en = timezone.now()
        solicitud.referencia_pago = (
            form.cleaned_data['referencia_pago'].strip()
            or solicitud.referencia_pago
        )
        solicitud.estado = 'pagada'
        solicitud.save()
        messages.success(
            request,
            f"Pago de {solicitud.folio} registrado (${solicitud.monto:.2f})."
        )
    else:
        messages.error(
            request,
            'No se pudo registrar el cobro.'
        )

    return redirect('solicitudes_certificados')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitud_entregar(request, pk):
    centro = request.centro
    solicitud = _solicitud_del_centro(centro, pk)

    if request.method != 'POST':
        return redirect('solicitudes_certificados')

    if solicitud.estado != 'pagada':
        messages.warning(
            request,
            f"La solicitud {solicitud.folio} debe estar pagada para entregarse."
        )
        return redirect('solicitudes_certificados')

    solicitud.estado = 'entregada'
    solicitud.entregado_por = request.user
    solicitud.entregado_en = timezone.now()
    solicitud.save()

    messages.success(
        request,
        f"Certificado {solicitud.folio} entregado."
    )
    return redirect('solicitudes_certificados')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def solicitud_anular(request, pk):
    centro = request.centro
    solicitud = _solicitud_del_centro(centro, pk)

    if request.method != 'POST':
        return redirect('solicitudes_certificados')

    if solicitud.estado in ('entregada', 'anulada', 'rechazada'):
        messages.warning(
            request,
            f"La solicitud {solicitud.folio} no se puede anular."
        )
        return redirect('solicitudes_certificados')

    if solicitud.pagado and solicitud.metodo_pago == 'online':
        reembolsar_pago_online(solicitud)

    solicitud.estado = 'anulada'
    solicitud.save()

    messages.success(
        request,
        f"Solicitud {solicitud.folio} anulada."
    )
    return redirect('solicitudes_certificados')