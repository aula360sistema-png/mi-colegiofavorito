from gettext import translation
import logging

logger = logging.getLogger(__name__)



# Create your views here.
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q

from administracion.views import obtener_centro_del_usuario
from core.decorators import centro_required, role_required
from .models import Asignatura, DocenteMateria
from docentes.models import Docente
from core.models import AnioEscolar
from academico.models import Grado, Seccion
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages

from estudiantes.models import HistorialAcademico, Inscripcion
from .models import Calificacion, Periodo, PeriodoAnio, Asignatura, Seccion, AreaCurricular
from .forms import CalificacionForm, SeccionForm, CompetenciaForm, AreaCurricularForm, AsignaturaForm, GradoAsignaturaForm
from core.models import CentroEducativo
from core.utils.anio import obtener_anio_activo
from academico.services.periodos import sincronizar_periodos_centro
from academico.services import estructura


from .models import Nivel
from .forms import NivelForm


from django.db import transaction

def asignar_docente2(request):
    if request.method == "POST":
        DocenteMateria.objects.create(
            docente_id=request.POST["docente"],
            asignatura_id=request.POST["asignatura"],
            grado_id=request.POST["grado"],
            seccion_id=request.POST["seccion"],
            anio_escolar=AnioEscolar.objects.get(activo=True)
        )
        return redirect("home")

    return render(request, "academico/asignar_docente.html", {
        "docentes": Docente.objects.all(),
        "asignaturas": Asignatura.objects.all(),
        "grados": Grado.objects.all(),
        "secciones": Seccion.objects.all()
    })
@login_required
def asignar_docente(request):
    centro = obtener_centro_del_usuario(request)

    if request.method == "POST":
        form = DocenteMateriaForm(request.POST, centro=centro)

        if form.is_valid():
            form.save()
            return redirect("docentemateria_list")
    else:
        form = DocenteMateriaForm(centro=centro)

    return render(request, "academico/asignar_docente.html", {
        "form": form,
        "accion": "Asignar docente"
    })


from .models import Calificacion, Periodo, Competencia, GradoAsignatura
from estudiantes.models import Inscripcion

from core.models import CentroEducativo


def get_centro_activo(request):
    user = request.user

    if not user.is_authenticated:
        return None

    # SUPERADMIN / ADMIN usan sesiÃ³n
    if user.rol in ('superadmin', 'admin'):
        centro_id = request.session.get('centro_id')
        if not centro_id:
            return None
        return CentroEducativo.objects.filter(id=centro_id).first()

    # DIRECTOR / SECRETARIA â†’ centro fijo
    if user.rol in ['director', 'secretaria']:
        if hasattr(user, 'administrativo'):
            return user.administrativo.centro

    # DOCENTE
    if user.rol == 'docente' and hasattr(user, 'docente'):
        return user.docente.centro

    # ESTUDIANTE
    if user.rol == 'estudiante' and hasattr(user, 'estudiante'):
        return user.estudiante.centro

    return None



# LISTAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def nivel_list(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    niveles = estructura.niveles(centro)

    stats = {
        'total': len(niveles),
        'grados': len(estructura.grados(centro)),
        'secciones': len(estructura.secciones(centro)),
    }

    page_obj = Paginator(niveles, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/nivel_list.html', {
        'niveles': page_obj.object_list,
        'page_obj': page_obj,
        'centro': centro,
        'stats': stats,
    })


# CREAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def nivel_create(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    if request.method == 'POST':
        form = NivelForm(request.POST)
        if form.is_valid():
            if Nivel.objects.filter(centro=centro).exists():
                form.add_error(
                    'tipo',
                    'Este centro ya tiene un nivel asignado. Para cambiar el '
                    'nivel del centro edite el centro educativo.'
                )
            else:
                nivel = form.save(commit=False)
                nivel.centro = centro
                nivel.save()
                return redirect('nivel_list')
    else:
        form = NivelForm()

    return render(request, 'academico/nivel_form.html', {
        'form': form,
        'accion': 'Crear'
    })



# EDITAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def nivel_update(request, pk):
    centro = get_centro_activo(request)
    nivel = get_object_or_404(Nivel, pk=pk, centro=centro)

    if request.method == 'POST':
        form = NivelForm(request.POST, instance=nivel)
        if form.is_valid():
            tipo_anterior = nivel.tipo
            if (
                form.cleaned_data['tipo'] != tipo_anterior
                and nivel.grado_set.exists()
            ):
                form.add_error(
                    'tipo',
                    'No puede cambiar el tipo de nivel porque ya tiene grados. '
                    'Edite el centro educativo para cambiar el nivel.'
                )
            elif Nivel.objects.filter(
                centro=centro, tipo=form.cleaned_data['tipo']
            ).exclude(pk=nivel.pk).exists():
                form.add_error(
                    'tipo',
                    'Este centro ya tiene un nivel de ese tipo.'
                )
            else:
                form.save()
                return redirect('nivel_list')
    else:
        form = NivelForm(instance=nivel)

    return render(request, 'academico/nivel_form.html', {
        'form': form,
        'accion': 'Editar'
    })
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def nivel_delete(request, pk):
    centro = get_centro_activo(request)
    if not centro:
        return JsonResponse({'success': False, 'error': 'Centro no activo'})

    try:
        nivel = Nivel.objects.get(pk=pk, centro=centro)
        nivel.delete()
        return JsonResponse({'success': True})
    except Nivel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Nivel no encontrado'})

from .models import Nivel, Grado
from .forms import GradoForm
from academico.services.estructura_minerd import crear_estructura_minerd

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def estructura_minerd(request):
    """Reconstruye/completa los grados MINERD del nivel del centro activo."""
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    tipos = list(
        Nivel.objects.filter(centro=centro).values_list('tipo', flat=True)
    )
    if not tipos:
        messages.warning(
            request,
            'Este centro no tiene un nivel asignado. Edite el centro '
            'educativo para elegir su nivel.'
        )
        return redirect('nivel_list')

    resultado = crear_estructura_minerd(centro, tipos)

    messages.success(
        request,
        f"Estructura del nivel lista: {len(resultado['niveles'])} nivel(es) "
        f"y {len(resultado['grados'])} grado(s) del currÃ­culo oficial."
    )
    return redirect('nivel_list')


# academico/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from academico.models import Grado, DocenteMateria
from core.models import AnioEscolar

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_asignaturas(request, grado_id):
    centro = get_centro_activo(request)

    grado = get_object_or_404(
        Grado,
        id=grado_id,
        nivel__centro=centro
    )

    anio_escolar = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

    asignaciones = DocenteMateria.objects.filter(
        grado=grado,
        anio_escolar=anio_escolar
    ).select_related(
        'asignatura',
        'docente',
        'seccion'
    ).order_by('seccion__nombre', 'asignatura__nombre')

    return render(request, 'academico/grado_asignaturas.html', {
        'grado': grado,
        'anio_escolar': anio_escolar,
        'asignaciones': asignaciones
    })



# academico/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from estudiantes.models import Inscripcion
from academico.models import Grado
from core.models import AnioEscolar
from collections import defaultdict




from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from estudiantes.models import Inscripcion
from academico.models import Grado
from core.models import AnioEscolar
from django.utils.timezone import now
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_estudiantes(request, grado_id):
    centro = get_centro_activo(request)

    grado = get_object_or_404(
        Grado,
        id=grado_id,
        nivel__centro=centro
    )

    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')

    # Año consultado: activo por defecto; ?anio=N permite revisar años
    # futuros (p. ej. recién promocionados) o históricos.
    anio_escolar = anios.filter(activo=True).first()
    anio_param = request.GET.get('anio')
    if anio_param:
        anio_escolar = get_object_or_404(
            AnioEscolar,
            pk=anio_param,
            centro=centro
        )

    inscripciones = Inscripcion.objects.filter(
        grado=grado,
        anio_escolar=anio_escolar,
        centro=centro
    ).select_related(
        'estudiante',
        'seccion'
    ).order_by(
        'seccion__nombre',
        'estudiante__primer_apellido',
        'estudiante__primer_nombre'
    )

    secciones = defaultdict(list)
    for ins in inscripciones:
        secciones[ins.seccion].append(ins)

    puede_mover = request.user.rol in (
        'director', 'secretaria', 'admin', 'superadmin'
    )

    return render(request, 'academico/grado_estudiantes.html', {
        'grado': grado,
        'anio_escolar': anio_escolar,
        'anios': anios,
        'secciones': dict(secciones),
        'secciones_grado': list(
            grado.secciones.values('id', 'nombre')
        ),
        'puede_mover': puede_mover,
    })


@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def inscripcion_cambiar_seccion(request, pk):
    """Mueve un estudiante a otra sección de su mismo grado."""
    from django.core.exceptions import ValidationError

    from .models import Seccion
    from .services.inscripciones import CambiarSeccionError, cambiar_seccion

    centro = get_centro_activo(request)
    inscripcion = get_object_or_404(Inscripcion, pk=pk, centro=centro)
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    error = None
    nueva = None
    try:
        seccion = Seccion.objects.get(
            pk=request.POST.get('seccion'),
            centro=centro,
        )
        _, nueva = cambiar_seccion(inscripcion, seccion, request.user)
    except Seccion.DoesNotExist:
        error = 'La sección indicada no existe en este centro.'
    except (TypeError, ValueError):
        error = 'Sección inválida.'
    except ValidationError as e:
        error = '; '.join(e.messages)
    except CambiarSeccionError as e:
        error = str(e)

    nombre = inscripcion.estudiante.nombre_completo()

    if es_ajax:
        if error:
            return JsonResponse(
                {'success': False, 'error': error},
                status=400,
            )
        return JsonResponse({
            'success': True,
            'mensaje': (
                f'{nombre} movido a la sección {nueva.nombre}.'
            ),
        })

    if error:
        messages.error(request, f'No se pudo cambiar la sección: {error}')
    else:
        messages.success(
            request,
            f'{nombre} movido a la sección {nueva.nombre}.'
        )
    return redirect('grado_estudiantes', grado_id=inscripcion.grado_id)

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def cerrar_todos_los_periodos(request):
    centro = get_centro_activo(request)
    if not centro:
        messages.error(request, "No hay un centro activo en sesión.")
        return redirect('core:seleccionar_centro')

    anio = obtener_anio_activo(centro)
    if not anio:
        messages.error(request, "No hay un año escolar activo.")
        return redirect('periodo_list')

    sincronizar_periodos_centro(centro)

    # ====================================
    # VALIDAR NOTAS PENDIENTES POR PERÍODO
    # ====================================
    from .services.cierre import pendientes_por_docente, rellenar_ceros_periodo

    abiertos = PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False,
    ).select_related('periodo')

    forzar = request.GET.get('forzar') == '1'
    puede_forzar = _puede_forzar_cierre(request.user)

    bloqueados = {}
    for estado in abiertos:
        pendientes = pendientes_por_docente(anio, estado.periodo)
        if pendientes:
            bloqueados[estado.periodo] = pendientes

    if bloqueados:
        if not forzar:
            detalle = '; '.join(
                f"{p.nombre} ({len(rows)} asignatura(s) incompleta(s))"
                for p, rows in bloqueados.items()
            )
            messages.error(
                request,
                f"No se pueden cerrar los períodos: hay notas pendientes "
                f"en {detalle}. Completa las calificaciones antes de cerrar."
            )
            if puede_forzar:
                messages.warning(
                    request,
                    "Como Dirección puedes forzar el cierre: se pondrán 0 "
                    "automáticos en las notas faltantes (queda auditado)."
                )
            return redirect('periodo_list')

        if not puede_forzar:
            messages.error(
                request,
                "Solo Dirección puede forzar el cierre con ceros automáticos."
            )
            return redirect('periodo_list')

        total_notas = 0
        for periodo_pendiente, filas in bloqueados.items():
            creados = rellenar_ceros_periodo(anio, periodo_pendiente)
            total_notas += creados
            _auditar_cierre_forzado(
                request,
                periodo_pendiente,
                anio,
                len(filas),
                creados,
            )

        if total_notas:
            messages.warning(
                request,
                f"⚠️ Cierre forzado: {total_notas} nota(s) puesta(s) en 0 "
                f"automáticamente (origen='sistema', auditado)."
            )

    # Cerrar todos los períodos del año activo
    count = PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False
    ).update(cerrado=True, fecha_cierre=now().date())

    # .update() masivo no dispara post_save: invalidar la caché aquí.
    from academico.services.estructura import invalidar_estructura
    invalidar_estructura(centro.id)

    messages.success(request, f"✅ Se cerraron {count} periodo(s) correctamente.")
    return redirect('periodo_list')

# LISTAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    grados = estructura.grados(centro)

    if q:
        ql = q.lower()
        grados = [
            g for g in grados
            if ql in g.nombre.lower()
            or ql in (g.nivel.nombre or '').lower()
        ]

    stats = {
        'total': len(estructura.grados(centro)),
        'niveles': len(estructura.niveles(centro)),
        'secciones': len(estructura.secciones(centro)),
    }

    page_obj = Paginator(grados, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/grado_list.html', {
        'grados': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': stats,
    })


# CREAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = GradoForm(request.POST, centro=centro)
        if form.is_valid():
            grado = form.save(commit=False)

            # ValidaciÃ³n extra de seguridad
            if grado.nivel.centro != centro:
                return redirect('grado_list')

            grado.save()
            form.save_m2m()
            return redirect('grado_list')
    else:
        form = GradoForm(centro=centro)
        form.fields['nivel'].queryset = Nivel.objects.filter(centro=centro)

    return render(request, 'academico/grado_form.html', {
        'form': form,
        'accion': 'Crear'
    })


# EDITAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_update(request, pk):
    centro = get_centro_activo(request)
    grado = get_object_or_404(
        Grado,
        pk=pk,
        nivel__centro=centro
    )

    if request.method == 'POST':
        form = GradoForm(request.POST, instance=grado, centro=centro)
        if form.is_valid():
            grado = form.save(commit=False)
            if grado.nivel.centro == centro:
                grado.save()
                form.save_m2m()
            return redirect('grado_list')
    else:
        form = GradoForm(instance=grado, centro=centro)
        form.fields['nivel'].queryset = Nivel.objects.filter(centro=centro)

    return render(request, 'academico/grado_form.html', {
        'form': form,
        'accion': 'Editar'
    })


# ELIMINAR
@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_delete(request, pk):
    grado = get_object_or_404(Grado, pk=pk)

    if request.method == 'POST':
        grado.delete()
        return JsonResponse({'success': True})

    return JsonResponse({
        'success': False,
        'error': 'MÃ©todo no permitido'
    })





@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def seccion_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    secciones = estructura.secciones(centro)

    if q:
        ql = q.lower()
        secciones = [
            s for s in secciones
            if ql in s.nombre.lower()
            or any(ql in g.nombre.lower() for g in s.grados.all())
        ]

    stats = {
        'total': len(estructura.secciones(centro)),
        'grados': len(estructura.grados(centro)),
    }

    page_obj = Paginator(secciones, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/seccion_list.html', {
        'secciones': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': stats,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def seccion_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = SeccionForm(request.POST, centro=centro)
        if form.is_valid():
            seccion = form.save(commit=False)
            seccion.centro = centro
            seccion.save()
            return redirect('seccion_list')
    else:
        form = SeccionForm(centro=centro)

    return render(request, 'academico/seccion_form.html', {
        'form': form,
        'accion': 'Crear'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def seccion_update(request, pk):
    centro = get_centro_activo(request)
    seccion = get_object_or_404(
        Seccion,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = SeccionForm(request.POST, instance=seccion, centro=centro)
        if form.is_valid():
            form.save()
            return redirect('seccion_list')
    else:
        form = SeccionForm(instance=seccion, centro=centro)

    return render(request, 'academico/seccion_form.html', {
        'form': form,
        'accion': 'Editar'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def seccion_delete(request, pk):
    seccion = get_object_or_404(Seccion, pk=pk)

    if request.method == 'POST':
        seccion.delete()
        return redirect('seccion_list')

    return redirect('seccion_list')




@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def area_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    areas = estructura.areas(centro)

    if q:
        ql = q.lower()
        areas = [a for a in areas if ql in a.nombre.lower()]

    stats = {
        'total': len(estructura.areas(centro)),
        'asignaturas': len(estructura.asignaturas(centro)),
    }

    page_obj = Paginator(areas, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/area_list.html', {
        'areas': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': stats,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def area_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = AreaCurricularForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.centro = centro
            area.save()
            return redirect('area_list')
    else:
        form = AreaCurricularForm()

    return render(request, 'academico/area_form.html', {
        'form': form,
        'accion': 'Crear'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def area_update(request, pk):
    centro = get_centro_activo(request)
    area = get_object_or_404(AreaCurricular, pk=pk, centro=centro)

    if request.method == 'POST':
        form = AreaCurricularForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            return redirect('area_list')
    else:
        form = AreaCurricularForm(instance=area)

    return render(request, 'academico/area_form.html', {
        'form': form,
        'accion': 'Editar'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def area_delete(request, pk):
    area = get_object_or_404(AreaCurricular, pk=pk)

    if request.method == 'POST':
        area.delete()
        return redirect('area_list')

    return redirect('area_list')



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def asignatura_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    asignaturas = estructura.asignaturas(centro)

    if q:
        ql = q.lower()
        asignaturas = [
            a for a in asignaturas
            if ql in a.nombre.lower()
            or ql in (a.area.nombre or '').lower()
        ]

    stats = {
        'total': len(estructura.asignaturas(centro)),
        'areas': len(estructura.areas(centro)),
    }

    page_obj = Paginator(asignaturas, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/asignatura_list.html', {
        'asignaturas': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': stats,
    })


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def ajax_asignaturas_por_grado(request, grado_id):
    centro = get_centro_activo(request)

    asignadas = GradoAsignatura.objects.filter(
        grado_id=grado_id
    ).values_list('asignatura_id', flat=True)

    asignaturas = Asignatura.objects.filter(
        centro=centro
    ).exclude(id__in=asignadas)

    data = {
        'asignaturas': [
            {'id': a.id, 'nombre': a.nombre}
            for a in asignaturas
        ]
    }

    return JsonResponse(data)




@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def asignatura_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = AsignaturaForm(
            request.POST,
            centro=centro
        )

        if form.is_valid():
            asignatura = form.save(commit=False)
            asignatura.centro = centro   # ðŸ” seguridad
            asignatura.save()

            messages.success(
                request,
                'Asignatura creada correctamente'
            )
            return redirect('asignatura_list')
    else:
        form = AsignaturaForm(centro=centro)

    return render(
        request,
        'academico/asignatura_form.html',
        {
            'form': form,
            'accion': 'Crear'
        }
    )




@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def asignatura_update(request, pk):
    centro = get_centro_activo(request)
    asignatura = get_object_or_404(Asignatura, pk=pk, centro=centro)

    if request.method == 'POST':
        form = AsignaturaForm(request.POST, instance=asignatura)
        if form.is_valid():
            form.save()
            return redirect('asignatura_list')
    else:
        form = AsignaturaForm(instance=asignatura)
        form.fields['area'].queryset = AreaCurricular.objects.filter(centro=centro)

    return render(request, 'academico/asignatura_form.html', {
        'form': form,
        'accion': 'Editar'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def asignatura_delete(request, pk):
    centro = get_centro_activo(request)

    asignatura = get_object_or_404(
        Asignatura,
        pk=pk,
        centro=centro
    )

    asignatura.delete()
    return redirect('asignatura_list')



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_asignatura_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    relaciones = estructura.grado_asignaturas(centro)

    if q:
        ql = q.lower()
        relaciones = [
            r for r in relaciones
            if ql in r.grado.nombre.lower()
            or ql in (r.grado.nivel.nombre or '').lower()
            or ql in r.asignatura.nombre.lower()
        ]

    stats = {
        'total': len(estructura.grado_asignaturas(centro)),
        'grados': len(estructura.grados(centro)),
        'asignaturas': len(estructura.asignaturas(centro)),
    }

    page_obj = Paginator(relaciones, 10).get_page(request.GET.get('page'))

    return render(
        request,
        'academico/grado_asignatura_list.html',
        {
            'relaciones': page_obj.object_list,
            'page_obj': page_obj,
            'q': q,
            'stats': stats,
        }
    )



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_asignatura_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = GradoAsignaturaForm(request.POST)
        form.fields['grado'].queryset = Grado.objects.filter(
            nivel__centro=centro
        )
        form.fields['asignatura'].queryset = Asignatura.objects.filter(
            centro=centro
        )

        if form.is_valid():
            relacion = form.save(commit=False)

            if (
                relacion.grado.nivel.centro != centro or
                relacion.asignatura.centro != centro
            ):
                return redirect('grado_asignatura_list')

            relacion.save()
            return redirect('grado_asignatura_list')

    else:
        form = GradoAsignaturaForm()
        form.fields['grado'].queryset = Grado.objects.filter(
            nivel__centro=centro
        )
        form.fields['asignatura'].queryset = Asignatura.objects.filter(
            centro=centro
        )

    return render(request, 'academico/grado_asignatura_form.html', {
        'form': form,
        'accion': 'Asignar'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def grado_asignatura_delete(request, pk):
    centro = get_centro_activo(request)
    relacion = get_object_or_404(
        GradoAsignatura,
        pk=pk,
        grado__nivel__centro=centro
    )

    if request.method == 'POST':
        relacion.delete()
        return redirect('grado_asignatura_list')

    return render(request, 'academico/grado_asignatura_delete.html', {
        'relacion': relacion
    })





@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def competencia_list(request):
    centro = get_centro_activo(request)

    competencias = estructura.competencias(centro)

    stats = {
        'total': len(competencias),
        'activas': sum(1 for c in competencias if c.activo),
    }

    page_obj = Paginator(competencias, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/competencia_list.html', {
        'competencias': page_obj.object_list,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def competencia_create(request):
    centro = get_centro_activo(request)
    form = CompetenciaForm(request.POST or None, centro=centro)

    if form.is_valid():
        form.save()
        messages.success(request, 'Competencia creada correctamente')
        return redirect('competencia_list')

    return render(request, 'academico/competencia_form.html', {
        'form': form,
        'titulo': 'Nueva Competencia'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def competencia_update(request, pk):
    centro = get_centro_activo(request)
    competencia = get_object_or_404(Competencia, pk=pk, nivel__centro=centro)
    form = CompetenciaForm(request.POST or None, instance=competencia, centro=centro)

    if form.is_valid():
        form.save()
        messages.success(request, 'Competencia actualizada correctamente')
        return redirect('competencia_list')

    return render(request, 'academico/competencia_form.html', {
        'form': form,
        'titulo': 'Editar Competencia'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def competencia_delete(request, pk):
    centro = get_centro_activo(request)
    competencia = get_object_or_404(Competencia, pk=pk, nivel__centro=centro)

    if request.method == 'POST':
        competencia.delete()
        messages.success(request, 'Competencia eliminada correctamente')
        return redirect('competencia_list')

    return render(request, 'academico/competencia_confirm_delete.html', {
        'competencia': competencia
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.deletion import ProtectedError
from .models import Periodo, PeriodoAnio
from .forms import PeriodoForm


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def periodo_list(request):
    centro = get_centro_activo(request)

    periodos = estructura.periodos(centro)

    anio = obtener_anio_activo(centro)
    estados = {}
    if anio:
        sincronizar_periodos_centro(centro)
        estados = {
            e.periodo_id: e
            for e in estructura.estados_periodo_anio(anio)
        }

    lista = [
        {'periodo': p, 'estado': estados.get(p.id)}
        for p in periodos
    ]

    abiertos = sum(1 for e in estados.values() if not e.cerrado)
    cerrados = sum(1 for e in estados.values() if e.cerrado)

    stats = {
        'total': len(lista),
        'abiertos': abiertos,
        'cerrados': cerrados,
        'anio': anio,
        'todos_cerrados': bool(estados) and abiertos == 0,
        'puede_forzar': _puede_forzar_cierre(request.user),
    }

    # Panel de notas pendientes (períodos abiertos del año activo):
    # docentes/asignaturas con estudiantes sin nota completa.
    from .services.cierre import pendientes_por_docente

    pendientes_por_periodo = []
    if anio:
        for item in lista:
            estado = item['estado']
            if not estado or estado.cerrado:
                continue
            filas_pendientes = pendientes_por_docente(anio, item['periodo'])
            if filas_pendientes:
                pendientes_por_periodo.append({
                    'periodo': item['periodo'],
                    'filas': filas_pendientes,
                    'estudiantes': max(
                        f['faltantes'] for f in filas_pendientes
                    ),
                })

    # Relación Período ↔ AñoEscolar (matriz para la pestaña "Relación")
    catalogo = list(periodos)
    anios_relacion = estructura.anios_escolares(centro)
    matriz = {}
    if anios_relacion:
        sincronizar_periodos_centro(centro)
        for e in estructura.matriz_periodos(centro):
            matriz[(e.periodo_id, e.anio_escolar_id)] = e

    filas = [
        {
            'anio': a,
            'estados': [matriz.get((p.id, a.id)) for p in catalogo],
        }
        for a in anios_relacion
    ]

    return render(request, 'academico/periodo_list.html', {
        'periodos': lista,
        'stats': stats,
        'catalogo': catalogo,
        'filas': filas,
        'pendientes_por_periodo': pendientes_por_periodo,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def periodo_create(request):
    centro = get_centro_activo(request)
    if request.method == 'POST':
        form = PeriodoForm(request.POST, centro=centro)
        if form.is_valid():
            periodo = form.save(commit=False)
            periodo.centro = centro
            periodo.save()
            sincronizar_periodos_centro(centro)
            return redirect('periodo_list')
    else:
        form = PeriodoForm(centro=centro)

    return render(request, 'academico/periodo_form.html', {
        'form': form,
        'accion': 'Nuevo Período'
    })



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def periodo_update(request, pk):
    centro = get_centro_activo(request)
    periodo = get_object_or_404(Periodo, pk=pk, centro=centro)

    if request.method == 'POST':
        form = PeriodoForm(request.POST, instance=periodo, centro=centro)
        if form.is_valid():
            form.save()
            return redirect('periodo_list')
    else:
        form = PeriodoForm(instance=periodo, centro=centro)

    return render(request, 'academico/periodo_form.html', {
        'form': form,
        'accion': 'Editar Período'
    })



@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def periodo_delete(request, pk):
    centro = get_centro_activo(request)
    periodo = get_object_or_404(Periodo, pk=pk, centro=centro)

    try:
        periodo.delete()
        return JsonResponse({'success': True})
    except ProtectedError:
        return JsonResponse({
            'success': False,
            'error': 'No se puede eliminar: el período tiene calificaciones registradas.'
        })


# ============================================
# HELPERS: CIERRE DE PERÍODOS CON VALIDACIÓN
# ============================================

ROLES_FORZAR_CIERRE = ('director', 'admin', 'superadmin')


def _puede_forzar_cierre(usuario):
    """Solo Dirección puede forzar cierre con ceros automáticos."""
    return getattr(usuario, 'rol', None) in ROLES_FORZAR_CIERRE


def _resumen_pendientes(pendientes):
    filas = pendientes[:5]
    resumen = '; '.join(
        f"{p['asignatura']} ({p['grado']}-{p['seccion']}): "
        f"{p['faltantes']} estudiante(s)"
        for p in filas
    )
    if len(pendientes) > len(filas):
        resumen += f" y {len(pendientes) - len(filas)} más"
    return resumen


def _auditar_cierre_forzado(request, periodo, anio, asignaturas, notas_creadas):
    """Deja constancia del cierre forzado con ceros automáticos."""
    try:
        from auditoria.services import registrar_evento

        registrar_evento(
            accion='CIERRE_FORZADO',
            descripcion=(
                f"Cierre forzado del período {periodo.nombre} "
                f"({anio.nombre}): {notas_creadas} nota(s) puesta(s) en 0 "
                f"(origen='sistema') por {asignaturas} asignatura(s) "
                f"incompleta(s)."
            ),
            usuario=request.user,
            modulo='ACADEMICO',
            modelo='PeriodoAnio',
            objeto_id=periodo.id,
            riesgo='ALTO',
            datos_nuevos={
                'periodo': periodo.nombre,
                'anio': anio.nombre,
                'asignaturas_pendientes': asignaturas,
                'notas_en_cero': notas_creadas,
            },
        )
    except Exception:
        logger.warning(
            'No se pudo auditar cierre forzado del período %s',
            periodo.id,
            exc_info=True,
        )


@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def alternar_periodo_anio(request, pk):
    """Abre o cierra un período del catálogo para el año escolar activo.

    Al cerrar valida que no haya estudiantes con notas incompletas.
    Si las hay, bloquea; solo Dirección puede forzar y en ese caso se
    rellenan los huecos con ceros automáticos auditados (origen='sistema').
    """
    from .services.cierre import pendientes_por_docente, rellenar_ceros_periodo

    centro = get_centro_activo(request)
    periodo = get_object_or_404(Periodo, pk=pk, centro=centro)

    anio = obtener_anio_activo(centro)
    if not anio:
        return JsonResponse({'success': False, 'error': 'No hay año escolar activo.'})

    estado, _ = PeriodoAnio.objects.get_or_create(
        periodo=periodo,
        anio_escolar=anio,
    )

    if not estado.cerrado:
        # Intento de cierre: validar notas pendientes primero.
        puede_forzar = _puede_forzar_cierre(request.user)
        forzar = request.POST.get('forzar') == '1'
        pendientes = pendientes_por_docente(anio, periodo)

        if pendientes and not (forzar and puede_forzar):
            # Payload liviano: al cliente solo le importan los conteos.
            for fila in pendientes:
                fila.pop('nombres', None)
                fila.pop('inscripciones', None)

            if not puede_forzar:
                return JsonResponse({
                    'success': False,
                    'bloqueado': True,
                    'puede_forzar': False,
                    'error': (
                        f'El período {periodo.nombre} tiene notas '
                        f'pendientes ({len(pendientes)} asignatura(s)). '
                        f'Solicita a Dirección completarlas o forzar el cierre.'
                    ),
                    'pendientes': pendientes,
                }, status=400)

            return JsonResponse({
                'success': False,
                'bloqueado': True,
                'puede_forzar': True,
                'error': (
                    f'El período {periodo.nombre} tiene notas pendientes: '
                    f'{_resumen_pendientes(pendientes)}. Completa las notas o '
                    f'fuerza el cierre (se pondrán 0 automáticos auditados).'
                ),
                'pendientes': pendientes,
            }, status=400)

        if pendientes and forzar:
            creados = rellenar_ceros_periodo(anio, periodo)
            _auditar_cierre_forzado(
                request, periodo, anio, len(pendientes), creados,
            )

    estado.cerrado = not estado.cerrado
    estado.fecha_cierre = now().date() if estado.cerrado else None
    estado.save()

    return JsonResponse({'success': True, 'cerrado': estado.cerrado})


from django.shortcuts import render, redirect, get_object_or_404
from .models import DocenteMateria
from .forms import DocenteMateriaForm



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docentemateria_list(request):
    centro = get_centro_activo(request)

    q = request.GET.get('q', '').strip()

    asignaciones = estructura.docentes_materia(centro)

    if q:
        ql = q.lower()
        asignaciones = [
            a for a in asignaciones
            if ql in (a.docente.primer_nombre or '').lower()
            or ql in (a.docente.segundo_nombre or '').lower()
            or ql in (a.docente.primer_apellido or '').lower()
            or ql in (a.docente.segundo_apellido or '').lower()
            or ql in a.asignatura.nombre.lower()
            or ql in a.grado.nombre.lower()
            or ql in (a.anio_escolar.nombre or '').lower()
        ]

    stats = {
        'total': len(estructura.docentes_materia(centro)),
        'docentes': len(Docente.objects.filter(centro=centro)),
        'grados': len(estructura.grados(centro)),
    }

    page_obj = Paginator(asignaciones, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/docentemateria_list.html', {
        'asignaciones': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'stats': stats,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docentemateria_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = DocenteMateriaForm(request.POST, centro=centro)
        if form.is_valid():
            form.save()
            return redirect('docentemateria_list')
    else:
        form = DocenteMateriaForm(centro=centro)

    return render(request, 'academico/docentemateria_form.html', {
        'form': form
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docentemateria_update(request, pk):
    centro = get_centro_activo(request)

    asignacion = get_object_or_404(
        DocenteMateria,
        pk=pk,
        docente__centro=centro
    )

    if request.method == 'POST':
        form = DocenteMateriaForm(
            request.POST,
            instance=asignacion,
            centro=centro
        )
        if form.is_valid():
            form.save()
            return redirect('docentemateria_list')
    else:
        form = DocenteMateriaForm(
            instance=asignacion,
            centro=centro
        )

    return render(request, 'academico/docentemateria_form.html', {
        'form': form
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docentemateria_delete(request, pk):
    centro = get_centro_activo(request)

    asignacion = get_object_or_404(
        DocenteMateria,
        pk=pk,
        docente__centro=centro
    )

    if request.method == 'POST':
        asignacion.delete()
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'MÃ©todo no permitido'}, status=405)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from administracion.models import AnioEscolar
from academico.forms import AnioEscolarForm


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def anio_escolar_list(request):
    centro = get_centro_activo(request)

    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')

    stats = {
        'total': anios.count(),
        'activos': anios.filter(activo=True).count(),
        'cerrados': anios.filter(cerrado=True).count(),
        'abiertos': anios.filter(cerrado=False).count(),
    }

    page_obj = Paginator(anios, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/anio_escolar_list.html', {
        'anios': page_obj.object_list,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def anio_escolar_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = AnioEscolarForm(request.POST)
        if form.is_valid():
            anio = form.save(commit=False)
            anio.centro = centro

            # Solo un aÃ±o activo por centro
            if anio.activo:
                AnioEscolar.objects.filter(
                    centro=centro,
                    activo=True
                ).update(activo=False)

            anio.save()
            return redirect('anio_escolar_list')
    else:
        form = AnioEscolarForm()

    return render(request, 'academico/anio_escolar_form.html', {
        'form': form,
        'accion': 'Crear'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def anio_escolar_update(request, pk):
    centro = get_centro_activo(request)

    anio = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = AnioEscolarForm(request.POST, instance=anio)
        if form.is_valid():

            if form.cleaned_data.get('activo'):
                AnioEscolar.objects.filter(
                    centro=centro,
                    activo=True
                ).exclude(pk=anio.pk).update(activo=False)

            form.save()
            return redirect('anio_escolar_list')
    else:
        form = AnioEscolarForm(instance=anio)

    return render(request, 'academico/anio_escolar_form.html', {
        'form': form,
        'accion': 'Editar'
    })




@login_required
@centro_required
@role_required('director', 'superadmin')
def cerrar_anio_escolar(request, pk):

    anio = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro
    )

    # ====================================
    # VALIDAR PERIODOS ABIERTOS
    # ====================================
    periodos_abiertos = PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False
    ).select_related('periodo')

    if periodos_abiertos.exists():

        detalle = ', '.join(
            f"{p.periodo.nombre} "
            f"({'completivo' if p.periodo.es_completivo else 'extraordinario' if p.periodo.es_extraordinario else 'regular'})"
            for p in periodos_abiertos
        )

        messages.error(
            request,
            f"No se puede cerrar el año escolar. Períodos abiertos: {detalle}."
        )

        return redirect('anio_escolar_list')

    # ====================================
    # VALIDAR ESTUDIANTES PENDIENTES
    # ====================================
    pendientes = Inscripcion.objects.filter(
        anio_escolar=anio,
        estado_final__in=['pendiente', 'sin_calificacion']
    ).select_related(
        'estudiante',
        'grado'
    )

    if pendientes.exists():

        request.session['pendientes_cierre'] = [
            {
                "estudiante": i.estudiante.nombre_completo(),
                "grado": str(i.grado),
                "promedio": str(i.promedio_final or "N/A"),
                "estado": i.estado_final,
            }
            for i in pendientes
        ]

        messages.error(
            request,
            f"No se puede cerrar el año escolar. Existen {pendientes.count()} estudiantes pendientes."
        )

        return redirect('anio_escolar_list')

    # ====================================
    # VALIDAR COMPLETIVO PENDIENTE (orden del cierre)
    # ====================================
    # Si hay estudiantes en 'recuperacion' y el centro usa completivo,
    # obliga a procesar primero cerrar_completivo; si no, la promoción
    # los marcaría para repetir sin haber evaluado su recuperación.
    from core.models import ConfiguracionCentro

    configuracion = ConfiguracionCentro.objects.filter(
        centro=anio.centro
    ).first()
    total_recup = Inscripcion.objects.filter(
        anio_escolar=anio,
        estado_final='recuperacion',
    ).count()
    if configuracion and configuracion.permite_completivo and total_recup:
        messages.error(
            request,
            f"No se puede cerrar el año: {total_recup} estudiante(s) están "
            f"en recuperación y el completivo aún no se ha procesado. "
            f"Ejecuta primero 'Cerrar completivo' (Boletines) con el "
            f"período de completivo cerrado."
        )
        return redirect('anio_escolar_list')

    # ====================================
    # CIERRE FINANCIERO (reporte de deudas)
    # ====================================
    from .services.cierre import deudores_del_anio, resumen_cierre

    deudores, total_deuda = deudores_del_anio(
        request.centro,
        anio,
    )

    config = getattr(request.centro, 'configuracion', None)
    if config is not None and getattr(
            config, 'bloquear_cierre_con_deudas', False):
        if deudores:
            messages.error(
                request,
                f"No se puede cerrar el año: {len(deudores)} estudiante(s) "
                f"con deuda (RD$ {total_deuda})."
            )
            return redirect('anio_escolar_list')

    # ====================================
    # CERRAR ANO ESCOLAR
    # ====================================
    try:

        totales = resumen_cierre(anio)

        with transaction.atomic():

            anio.cerrar()

            for inscripcion in Inscripcion.objects.filter(
                anio_escolar=anio
            ):

                HistorialAcademico.objects.update_or_create(
                    estudiante=inscripcion.estudiante,
                    nivel=inscripcion.grado.nivel,
                    grado=inscripcion.grado,
                    seccion=inscripcion.seccion,
                    anio_escolar=anio,
                    defaults={
                        "estado": inscripcion.estado_final,
                        "cerrado": True,
                    }
                )

            from core.models import CierreAnio

            CierreAnio.objects.update_or_create(
                anio_escolar=anio,
                defaults={
                    'usuario': request.user,
                    'totales': totales,
                    'deudores': deudores,
                    'total_deuda': total_deuda,
                    'reabierto': False,
                    'motivo_reapertura': '',
                    'usuario_reapertura': None,
                    'fecha_reapertura': None,
                },
            )

        aviso_deuda = ''
        if deudores:
            aviso_deuda = (
                f" Deuda pendiente registrada: {len(deudores)} "
                f"estudiante(s), RD$ {total_deuda}."
            )

        messages.success(
            request,
            f"Año escolar {anio.nombre} cerrado correctamente."
            f"{aviso_deuda}"
        )

    except Exception as e:

        messages.error(
            request,
            f"Error al cerrar el año escolar: {e}"
        )

    return redirect('anio_escolar_list')


@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def reabrir_anio_escolar(request, pk):
    """Reapertura supervisada: requiere motivo y queda auditada."""
    anio = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro,
        cerrado=True,
    )

    if request.method != 'POST':
        messages.error(request, 'Solicitud inválida.')
        return redirect('anio_escolar_list')

    motivo = (request.POST.get('motivo') or '').strip()
    if len(motivo) < 10:
        messages.error(
            request,
            'Debes indicar un motivo de al menos 10 caracteres.'
        )
        return redirect('anio_escolar_list')

    with transaction.atomic():
        anio.cerrado = False
        anio.save(update_fields=['cerrado'])

        from core.models import CierreAnio

        CierreAnio.objects.filter(anio_escolar=anio).update(
            reabierto=True,
            motivo_reapertura=motivo,
            usuario_reapertura=request.user,
            fecha_reapertura=timezone.now(),
        )

    messages.warning(
        request,
        f"Año {anio.nombre} REABIERTO. El historial académico generado se "
        f"mantendrá; al volver a cerrar se actualizará."
    )
    return redirect('anio_escolar_list')


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def crear_anio_siguiente(request, pk):
    """Paso 1 del asistente: crear el año que sigue a uno cerrado."""
    origen = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro,
    )

    import datetime as dt

    nombre_sugerido = f"{origen.fecha_fin.year}-{origen.fecha_fin.year + 1}"

    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip()
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')

        if not (nombre and fecha_inicio and fecha_fin):
            messages.error(
                request,
                'Nombre y fechas son obligatorios.'
            )
            return redirect('crear_anio_siguiente', pk=origen.pk)

        if AnioEscolar.objects.filter(
                centro=request.centro, nombre=nombre).exists():
            messages.error(
                request,
                f'Ya existe un año "{nombre}" en este centro.'
            )
            return redirect('crear_anio_siguiente', pk=origen.pk)

        nuevo = AnioEscolar.objects.create(
            centro=request.centro,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activo=False,
            cerrado=False,
        )

        sincronizar_periodos_anio(nuevo)

        messages.success(
            request,
            f"Año {nombre} creado con sus períodos. "
            f"Continúa con la promoción masiva."
        )
        return redirect('promocion_preview', pk=origen.pk)

    return render(
        request,
        'academico/anio_siguiente_form.html',
        {
            'origen': origen,
            'nombre_sugerido': nombre_sugerido,
            'inicio_sugerido': origen.fecha_fin + dt.timedelta(days=1),
            'fin_sugerido': (
                origen.fecha_fin + dt.timedelta(days=365)
            ),
        },
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def promocion_preview(request, pk):
    """Paso 2 del asistente: plan de promoción masiva.

    Muestra qué hará con cada estudiante y permite elegir la sección
    destino por cada grado antes de ejecutar.
    """
    from .services.cierre import calcular_promociones

    origen = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro,
    )

    destino = (
        AnioEscolar.objects
        .filter(centro=request.centro)
        .exclude(pk=origen.pk)
        .filter(fecha_inicio__gt=origen.fecha_inicio)
        .order_by('fecha_inicio')
        .first()
    )

    plan = calcular_promociones(origen)

    resumen = {'promover': 0, 'repetir': 0, 'egresado': 0, 'omitir': 0}
    for fila in plan:
        resumen[fila['accion']] += 1

    # Advertencia: estudiantes en 'recuperacion' que el plan manda a
    # repetir; si el completivo sigue pendiente, conviene procesarlo
    # antes de ejecutar la promoción.
    from core.models import ConfiguracionCentro

    configuracion = ConfiguracionCentro.objects.filter(
        centro=origen.centro
    ).first()
    recuperacion_en_plan = sum(
        1 for fila in plan
        if fila['estado'] == 'recuperacion'
    )
    advertencia_completivo = bool(
        configuracion
        and configuracion.permite_completivo
        and recuperacion_en_plan
    )

    grados_destino = {}
    for fila in plan:
        if fila['destino']:
            grados_destino[fila['destino'].id] = fila['destino']

    secciones_por_grado = {
        grado.id: list(
            Seccion.objects.filter(
                centro=request.centro,
                grados=grado,
            ).order_by('nombre')
        )
        for grado in grados_destino.values()
    }

    return render(
        request,
        'academico/promocion_preview.html',
        {
            'origen': origen,
            'destino': destino,
            'plan': plan,
            'resumen': resumen,
            'grados_destino': grados_destino.values(),
            'secciones_por_grado': secciones_por_grado,
            'recuperacion_en_plan': recuperacion_en_plan,
            'advertencia_completivo': advertencia_completivo,
        },
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def promocion_ejecutar(request, pk):
    """Paso 3 del asistente: ejecutar la matrícula masiva."""
    from .services.cierre import ejecutar_promocion

    origen = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro,
        cerrado=True,
    )

    if request.method != 'POST':
        return redirect('promocion_preview', pk=origen.pk)

    destino_id = request.POST.get('anio_destino')
    destino = get_object_or_404(
        AnioEscolar,
        pk=destino_id,
        centro=request.centro,
    )

    secciones_por_grado = {
        key.replace('seccion_', ''): value
        for key, value in request.POST.items()
        if key.startswith('seccion_') and value
    }

    solo = request.POST.getlist('estudiantes')
    solo_ids = (
        {int(x) for x in solo if str(x).isdigit()}
        if solo else None
    )

    creadas, omitidas = ejecutar_promocion(
        origen,
        destino,
        request.user,
        secciones_por_grado,
        solo_estudiantes=solo_ids,
    )

    messages.success(
        request,
        f"Promoción completada: {creadas} inscripción(es) creada(s) en "
        f"{destino.nombre}. Omitidas: {omitidas}."
    )
    return redirect('anio_escolar_list')


@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def respaldo_anio(request, pk):
    """Descarga JSON con los datos académicos/financieros del año."""
    from django.http import JsonResponse

    anio = get_object_or_404(
        AnioEscolar,
        pk=pk,
        centro=request.centro,
    )

    inscripciones = (
        Inscripcion.objects
        .filter(anio_escolar=anio)
        .select_related('estudiante', 'grado', 'seccion')
    )

    datos_inscripciones = []
    for i in inscripciones:
        datos_inscripciones.append({
            'matricula': i.estudiante.matricula,
            'estudiante': i.estudiante.nombre_completo(),
            'sexo': i.estudiante.sexo,
            'fecha_nacimiento': str(i.estudiante.fecha_nacimiento),
            'grado': str(i.grado),
            'seccion': str(i.seccion),
            'estado_final': i.estado_final,
            'promedio_final': str(i.promedio_final or ''),
        })

    historial = [
        {
            'matricula': h.estudiante.matricula,
            'nivel': str(h.nivel),
            'grado': str(h.grado),
            'seccion': str(h.seccion),
            'estado': h.estado,
        }
        for h in HistorialAcademico.objects.filter(
            anio_escolar=anio,
        ).select_related('estudiante', 'nivel', 'grado', 'seccion')
    ]

    calificaciones = [
        {
            'matricula': c.inscripcion.estudiante.matricula,
            'asignatura': str(c.asignatura),
            'competencia': str(c.competencia),
            'periodo': str(c.periodo),
            'nota': str(c.nota),
        }
        for c in Calificacion.objects.filter(
            inscripcion__anio_escolar=anio,
        ).select_related(
            'inscripcion__estudiante',
            'asignatura',
            'competencia',
            'periodo',
        )[:20000]
    ]

    bitacora = None
    cierre = getattr(anio, 'cierre', None)
    if cierre:
        bitacora = {
            'cerrado_por': cierre.usuario.username,
            'fecha_cierre': cierre.fecha.isoformat(),
            'totales': cierre.totales,
            'deudores': cierre.deudores,
            'total_deuda': str(cierre.total_deuda),
            'reabierto': cierre.reabierto,
            'motivo_reapertura': cierre.motivo_reapertura,
        }

    respuesta = JsonResponse({
        'centro': {
            'codigo_minerd': request.centro.codigo_minerd,
            'nombre': request.centro.nombre,
        },
        'anio_escolar': {
            'nombre': anio.nombre,
            'fecha_inicio': str(anio.fecha_inicio),
            'fecha_fin': str(anio.fecha_fin),
        },
        'bitacora_cierre': bitacora,
        'inscripciones': datos_inscripciones,
        'historial_academico': historial,
        'calificaciones': calificaciones,
    })

    respuesta['Content-Disposition'] = (
        f'attachment; filename="respaldo_{request.centro.codigo_minerd}'
        f'_{anio.nombre}.json"'
    )
    return respuesta


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def acta_seccion(request):
    """Acta consolidada de cierre por grado/sección (imprimible)."""
    anio_id = request.GET.get('anio')
    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')

    anio = None
    if anio_id:
        anio = get_object_or_404(
            AnioEscolar, pk=anio_id, centro=request.centro
        )
    else:
        anio = obtener_anio_activo(request.centro)

    inscripciones = Inscripcion.objects.none()
    if anio and grado_id:
        filtros = {
            'anio_escolar': anio,
            'grado_id': grado_id,
        }
        if seccion_id:
            filtros['seccion_id'] = seccion_id

        inscripciones = (
            Inscripcion.objects
            .filter(centro=request.centro, **filtros)
            .select_related('estudiante', 'grado', 'seccion')
            .order_by(
                'seccion__nombre',
                'estudiante__primer_apellido',
                'estudiante__primer_nombre',
            )
        )

    return render(
        request,
        'academico/acta_seccion.html',
        {
            'anio': anio,
            'inscripciones': inscripciones,
            'centro': request.centro,
            'fecha_emision': timezone.localdate(),
        },
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def curriculo(request):
    centro = get_centro_activo(request)

    areas = estructura.areas(centro)
    asignaturas = estructura.asignaturas(centro)
    relaciones = estructura.grado_asignaturas(centro)
    competencias = estructura.competencias(centro)
    asignaciones = estructura.docentes_materia(centro)

    page_areas = Paginator(areas, 10).get_page(request.GET.get('page_areas'))
    page_asignaturas = Paginator(asignaturas, 10).get_page(
        request.GET.get('page_asignaturas')
    )
    page_relaciones = Paginator(relaciones, 10).get_page(
        request.GET.get('page_relaciones')
    )
    page_competencias = Paginator(competencias, 10).get_page(
        request.GET.get('page_competencias')
    )
    page_asignaciones = Paginator(asignaciones, 10).get_page(
        request.GET.get('page_asignaciones')
    )

    stats = {
        'areas': page_areas.paginator.count,
        'asignaturas': page_asignaturas.paginator.count,
        'relaciones': page_relaciones.paginator.count,
        'competencias': page_competencias.paginator.count,
        'docentematerias': page_asignaciones.paginator.count,
    }

    return render(request, 'academico/curriculo.html', {
        'areas': page_areas,
        'asignaturas': page_asignaturas,
        'relaciones': page_relaciones,
        'competencias': page_competencias,
        'asignaciones': page_asignaciones,
        'stats': stats,
    })


# ============================================================
# HORARIO DE CLASES
# ============================================================

from .models import FranjaHoraria, HorarioClase
from .forms import FranjaHorariaForm, HorarioClaseForm


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def franja_list(request):
    centro = get_centro_activo(request)

    franjas = estructura.franjas(centro)

    page_obj = Paginator(franjas, 10).get_page(request.GET.get('page'))

    return render(request, 'academico/franja_list.html', {
        'franjas': page_obj.object_list,
        'page_obj': page_obj,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def franja_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = FranjaHorariaForm(request.POST, centro=centro)
        if form.is_valid():
            franja = form.save(commit=False)
            franja.centro = centro
            franja.save()
            messages.success(request, "Franja horaria creada correctamente.")
            return redirect('franja_list')
    else:
        form = FranjaHorariaForm(centro=centro)

    return render(request, 'academico/franja_form.html', {
        'form': form,
        'accion': 'Nueva Franja Horaria'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def franja_update(request, pk):
    centro = get_centro_activo(request)
    franja = get_object_or_404(FranjaHoraria, pk=pk, centro=centro)

    if request.method == 'POST':
        form = FranjaHorariaForm(request.POST, instance=franja, centro=centro)
        if form.is_valid():
            form.save()
            messages.success(request, "Franja horaria actualizada correctamente.")
            return redirect('franja_list')
    else:
        form = FranjaHorariaForm(instance=franja, centro=centro)

    return render(request, 'academico/franja_form.html', {
        'form': form,
        'accion': 'Editar Franja Horaria'
    })


@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def franja_delete(request, pk):
    centro = get_centro_activo(request)
    franja = get_object_or_404(FranjaHoraria, pk=pk, centro=centro)

    try:
        franja.delete()
        return JsonResponse({'success': True})
    except ProtectedError:
        return JsonResponse({
            'success': False,
            'error': 'No se puede eliminar: la franja tiene clases programadas.'
        })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def horario_list(request):
    centro = get_centro_activo(request)

    grados = sorted(
        estructura.grados(centro),
        key=lambda g: (g.nivel.tipo, g.orden, g.nombre),
    )

    secciones = estructura.secciones(centro)

    anio = obtener_anio_activo(centro)
    anios = estructura.anios_escolares(centro)

    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')
    anio_id = request.GET.get('anio')

    grado = None
    seccion = None
    anio_seleccionado = None

    if grado_id:
        grado = get_object_or_404(Grado, pk=grado_id, nivel__centro=centro)
    if seccion_id:
        seccion = get_object_or_404(Seccion, pk=seccion_id, centro=centro)
    if anio_id:
        anio_seleccionado = get_object_or_404(AnioEscolar, pk=anio_id, centro=centro)
    else:
        anio_seleccionado = anio

    franjas = estructura.franjas(centro)

    matriz = {}
    asignaciones_seccion = []

    if grado and seccion and anio_seleccionado:
        asignaciones_seccion = [
            a for a in estructura.docentes_materia(centro)
            if a.grado_id == grado.id
            and a.seccion_id == seccion.id
            and a.anio_escolar_id == anio_seleccionado.id
        ]

        clases = estructura.horario_clases_por_filtro(
            centro, grado, seccion, anio_seleccionado
        )

        for c in clases:
            matriz[(c.dia_semana, c.franja_id)] = c

    stats = {
        'grados': len(grados),
        'secciones': len(secciones),
        'franjas': len(franjas),
        'clases': len(estructura.horario_clases(centro)),
    }

    return render(request, 'academico/horario_list.html', {
        'grados': grados,
        'secciones': secciones,
        'anios': anios,
        'grado': grado,
        'seccion': seccion,
        'anio_seleccionado': anio_seleccionado,
        'franjas': franjas,
        'matriz': matriz,
        'asignaciones_seccion': asignaciones_seccion,
        'stats': stats,
        'DIAS_SEMANA': HorarioClase.DIAS_SEMANA,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def horario_clase_create(request):
    centro = get_centro_activo(request)

    grado_id = request.GET.get('grado')
    seccion_id = request.GET.get('seccion')

    if request.method == 'POST':
        form = HorarioClaseForm(request.POST, centro=centro)
        if form.is_valid():
            form.save()
            messages.success(request, "Clase agregada al horario correctamente.")

            url = reverse('horario_list')
            params = []
            if grado_id:
                params.append(f'grado={grado_id}')
            if seccion_id:
                params.append(f'seccion={seccion_id}')
            if params:
                url += '?' + '&'.join(params)
            return redirect(url)
    else:
        initial = {}
        if grado_id and seccion_id:
            asignacion = DocenteMateria.objects.filter(
                grado_id=grado_id,
                seccion_id=seccion_id,
                anio_escolar__activo=True,
                anio_escolar__centro=centro,
                docente__centro=centro
            ).first()
            if asignacion:
                initial['asignacion'] = asignacion.pk

        dia = request.GET.get('dia')
        if dia:
            try:
                initial['dia_semana'] = int(dia)
            except (ValueError, TypeError):
                pass

        form = HorarioClaseForm(centro=centro, initial=initial)

    return render(request, 'academico/horario_clase_form.html', {
        'form': form,
        'accion': 'Agregar Clase al Horario'
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def horario_clase_update(request, pk):
    centro = get_centro_activo(request)

    clase = get_object_or_404(
        HorarioClase,
        pk=pk,
        asignacion__docente__centro=centro
    )

    if request.method == 'POST':
        form = HorarioClaseForm(request.POST, instance=clase, centro=centro)
        if form.is_valid():
            form.save()
            messages.success(request, "Clase actualizada correctamente.")

            url = reverse('horario_list')
            url += f'?grado={clase.asignacion.grado_id}&seccion={clase.asignacion.seccion_id}'
            return redirect(url)
    else:
        form = HorarioClaseForm(instance=clase, centro=centro)

    return render(request, 'academico/horario_clase_form.html', {
        'form': form,
        'accion': 'Editar Clase del Horario'
    })


@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def horario_clase_delete(request, pk):
    centro = get_centro_activo(request)

    clase = get_object_or_404(
        HorarioClase,
        pk=pk,
        asignacion__docente__centro=centro
    )

    clase.delete()
    return JsonResponse({'success': True})
