from gettext import translation
import logging

logger = logging.getLogger(__name__)



# Create your views here.
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
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

    # SUPERADMIN usa sesiÃ³n
    if user.rol == 'superadmin':
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

    anio_escolar = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

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
        secciones[ins.seccion].append(ins.estudiante)

    return render(request, 'academico/grado_estudiantes.html', {
        'grado': grado,
        'anio_escolar': anio_escolar,
        'secciones': dict(secciones)
    })

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
    }

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


@login_required
@require_POST
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def alternar_periodo_anio(request, pk):
    """Abre o cierra un período del catálogo para el año escolar activo."""
    centro = get_centro_activo(request)
    periodo = get_object_or_404(Periodo, pk=pk, centro=centro)

    anio = obtener_anio_activo(centro)
    if not anio:
        return JsonResponse({'success': False, 'error': 'No hay año escolar activo.'})

    estado, _ = PeriodoAnio.objects.get_or_create(
        periodo=periodo,
        anio_escolar=anio,
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
    # VALIDAR PERÃODOS ABIERTOS
    # ====================================
    if PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False
    ).exists():

        messages.error(
            request,
            "No se puede cerrar el aÃ±o escolar. Existen perÃ­odos abiertos."
        )

        return redirect('anio_escolar_list')

    # ====================================
    # VALIDAR ESTUDIANTES PENDIENTES
    # ====================================
    pendientes = Inscripcion.objects.filter(
        anio_escolar=anio,
        estado_final__in = ['pendiente', 'sin_calificacion']
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
            f"No se puede cerrar el aÃ±o escolar. Existen {pendientes.count()} estudiantes pendientes."
        )

        return redirect('anio_escolar_list')

    # ====================================
    # CERRAR AÃ‘O ESCOLAR
    # ====================================
    try:

        with transaction.atomic():

            anio.cerrar()

            for inscripcion in Inscripcion.objects.filter(
                anio_escolar=anio
            ):

                HistorialAcademico.objects.get_or_create(
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

        messages.success(
            request,
            f"AÃ±o escolar {anio.nombre} cerrado correctamente."
        )

    except Exception as e:

        messages.error(
            request,
            f"Error al cerrar el aÃ±o escolar: {e}"
        )

    return redirect('anio_escolar_list')


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
