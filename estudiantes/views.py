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
from django.contrib import messages
from .forms import InscripcionAvanzadaForm


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string
from usuarios.models import Usuario
from django.db.models import Prefetch

from core.utils.session import get_centro_activo
from .utils import validar_promocion_estudiante
from core.utils.anio import obtener_anio_activo
from django.utils import timezone


@login_required
def estudiante_inicio(request):
    if request.user.rol != 'estudiante':
        return redirect('core:home')

    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user
    )

    return render(request, 'estudiantes/estudiante_inicio.html', {
        'estudiante': estudiante,
    })


@login_required
def estudiante_create(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('core:seleccionar_centro')

    if request.method == 'POST':

        form = EstudianteForm(request.POST)

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
            usuario.save()

            estudiante.usuario = usuario
            estudiante.save()

            return render(
                request,
                'estudiantes/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password
                }
            )

    else:
        form = EstudianteForm()

    return render(
        request,
        'estudiantes/estudiante_form.html',
        {
            'form': form,
            'estudiante': None
        }
    )

@login_required
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
            instance=estudiante
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
            instance=estudiante
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

    context = {
        'estudiante': estudiante,
        'inscripciones': inscripciones,
        'inscripcion_actual': inscripcion_actual,
    }

    return render(
        request,
        'estudiantes/estudiante_detail.html',
        context
    )
@login_required
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
def estudiante_list(request):

    centro = request.centro

    q = request.GET.get("q", "").strip()

    anio_activo = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

    estudiantes = Estudiante.objects.filter(
        centro=centro
    )

    if q:
        estudiantes = estudiantes.filter(
            Q(matricula__icontains=q) |
            Q(primer_nombre__icontains=q) |
            Q(segundo_nombre__icontains=q) |
            Q(primer_apellido__icontains=q) |
            Q(segundo_apellido__icontains=q)
        )

    estudiantes = estudiantes.prefetch_related(
        Prefetch(
            'inscripcion_set',
            queryset=Inscripcion.objects.filter(
                anio_escolar=anio_activo
            ).select_related(
                'grado',
                'seccion',
                'anio_escolar'
            ),
            to_attr='inscripcion_actual'
        )
    ).order_by(
        'primer_apellido',
        'segundo_apellido',
        'primer_nombre'
    )

    return render(
        request,
        'estudiantes/estudiante_list.html',
        {
            'estudiantes': estudiantes,
            'centro': centro,
            'anio_activo': anio_activo,
            'q': q,
        }
    )


@login_required
def ajax_cargar_secciones(request):
    grado_id = request.GET.get('grado')

    secciones = Seccion.objects.filter(
        grado_id=grado_id
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
        grado__nivel__centro=centro
    ).order_by('nombre')

    inscripciones = (
        Inscripcion.objects
        .filter(centro=centro)
        .select_related(
            'estudiante',
            'grado',
            'seccion',
            'anio_escolar'
        )
    )

    if q:
        inscripciones = inscripciones.filter(
            Q(estudiante__primer_nombre__icontains=q) |
            Q(estudiante__primer_apellido__icontains=q) |
            Q(estudiante__matricula__icontains=q)
        )

    if anio_id:
        inscripciones = inscripciones.filter(
            anio_escolar_id=anio_id
        )

    if grado_id:
        inscripciones = inscripciones.filter(
            grado_id=grado_id
        )

    if seccion_id:
        inscripciones = inscripciones.filter(
            seccion_id=seccion_id
        )

    if estado:
        inscripciones = inscripciones.filter(
            estado_final=estado
        )

    inscripciones = inscripciones.order_by(
        '-anio_escolar__fecha_inicio',
        'grado__nombre',
        'seccion__nombre',
        'estudiante__primer_apellido'
    )

    total_registros = inscripciones.count()

    context = {
        'centro': centro,
        'inscripciones': inscripciones,

        'anios': anios,
        'grados': grados,
        'secciones': secciones,

        'q': q,
        'estado': estado,

        'anio_seleccionado': anio_id,
        'grado_seleccionado': grado_id,
        'seccion_seleccionada': seccion_id,

        'total_registros': total_registros,
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

    estudiantes = Estudiante.objects.filter(centro=centro)

    if q:
        estudiantes = estudiantes.filter(
            Q(matricula__icontains=q) |
            Q(primer_nombre__icontains=q) |
            Q(primer_apellido__icontains=q)
        )

    estudiantes = estudiantes.order_by('primer_apellido', 'primer_nombre')

    inscripciones = {
        i.estudiante_id: i
        for i in (
            Inscripcion.objects
            .filter(
                centro=centro,
                anio_escolar=anio_actual
            )
            .select_related('grado', 'seccion')
        )
    }

    for e in estudiantes:
        i = inscripciones.get(e.id)
        e.constancia_grado = i.grado if i and i.grado else None
        e.constancia_seccion = i.seccion if i and i.seccion else None

    return render(request, 'estudiantes/constancias.html', {
        'centro': centro,
        'anio_actual': anio_actual,
        'estudiantes': estudiantes,
        'q': q,
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