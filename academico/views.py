from gettext import translation
import logging

logger = logging.getLogger(__name__)



# Create your views here.
from django.shortcuts import render, redirect

from administracion.views import obtener_centro_del_usuario
from core.decorators import centro_required, role_required
from .models import Asignatura, DocenteMateria
from docentes.models import Docente
from core.models import AnioEscolar
from academico.models import Grado, Seccion
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from estudiantes.models import HistorialAcademico, Inscripcion
from .models import Calificacion, Periodo, Asignatura, Seccion, AreaCurricular
from .forms import CalificacionForm, SeccionForm, CompetenciaForm, AreaCurricularForm, AsignaturaForm, GradoAsignaturaForm
from core.models import CentroEducativo


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




@login_required
def registrar_calificaciones(request, inscripcion_id, asignatura_id):
    logger.debug('Entrando a registrar_calificaciones')

    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    inscripcion = get_object_or_404(
        Inscripcion,
        id=inscripcion_id,
        centro=centro
    )
    logger.debug('Inscripción: %s', inscripcion)

    asignatura = get_object_or_404(
        Asignatura,
        id=asignatura_id,
        centro=centro
    )
    logger.debug('Asignatura: %s', asignatura)

    periodos = Periodo.objects.filter(
        centro=centro,
        activo=True
    ).order_by('orden')

    if not periodos.exists():
        messages.error(request, 'No hay períodos activos')
        return redirect('estudiante_detail', pk=inscripcion.estudiante.id)

    periodo = periodos.first()
    logger.debug('Período activo: %s', periodo)

    calificaciones = Calificacion.objects.filter(
        inscripcion=inscripcion,
        asignatura=asignatura,
        periodo=periodo
    )

    if request.method == 'POST':
        logger.debug('POST recibido: %s', request.POST)

        form = CalificacionForm(
            request.POST,
            asignatura=asignatura
        )

        if form.is_valid():
            competencia = form.cleaned_data['competencia']

            existe = Calificacion.objects.filter(
                inscripcion=inscripcion,
                asignatura=asignatura,
                competencia=competencia,
                periodo=periodo
            ).exists()

            logger.debug('¿Existe ya la nota?: %s', existe)

            if existe:
                messages.warning(
                    request,
                    'Ya existe una calificación para esta competencia'
                )
            else:
                calificacion = form.save(commit=False)
                calificacion.inscripcion = inscripcion
                calificacion.asignatura = asignatura
                calificacion.periodo = periodo
                calificacion.save()

                logger.debug('Nota guardada: %s', calificacion.nota)

                messages.success(request, 'Calificación registrada')
                return redirect(
                    'registrar_calificaciones',
                    inscripcion_id=inscripcion.id,
                    asignatura_id=asignatura.id
                )
        else:
            logger.warning('Errores de formulario: %s', form.errors)

    else:
        form = CalificacionForm(asignatura=asignatura)

    return render(
        request,
        'academico/registrar_calificaciones.html',
        {
            'inscripcion': inscripcion,
            'asignatura': asignatura,
            'periodo': periodo,
            'form': form,
            'calificaciones': calificaciones
        }
    )



from core.models import CentroEducativo

def get_centro_activo(request):
    user = request.user

    if not user.is_authenticated:
        return None

    # SUPERADMIN usa sesión
    if user.rol == 'superadmin':
        centro_id = request.session.get('centro_id')
        if not centro_id:
            return None
        return CentroEducativo.objects.filter(id=centro_id).first()

    # DIRECTOR / SECRETARIA → centro fijo
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
def nivel_list(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    niveles = Nivel.objects.filter(centro=centro)

    return render(request, 'academico/nivel_list.html', {
        'niveles': niveles,
        'centro': centro
    })


# CREAR
@login_required
def nivel_create(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    if request.method == 'POST':
        form = NivelForm(request.POST)
        if form.is_valid():
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
def nivel_update(request, pk):
    centro = get_centro_activo(request)
    nivel = get_object_or_404(Nivel, pk=pk, centro=centro)

    if request.method == 'POST':
        form = NivelForm(request.POST, instance=nivel)
        if form.is_valid():
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

# academico/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from academico.models import Grado, DocenteMateria
from core.models import AnioEscolar

@login_required
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
def cerrar_todos_los_periodos(request):
    centro = get_centro_activo(request)
    if not centro:
        messages.error(request, "No hay un centro activo en sesión.")
        return redirect('core:seleccionar_centro')

    # Cerrar todos los periodos del centro
    periodos = Periodo.objects.filter(centro=centro, cerrado=False)
  #  count = periodos.update(cerrado=True, fecha_cierre=now().date())
  # eso que esta comentado, es para hacer el cierre automatico con la fecha
    count = periodos.update(cerrado=True)

    messages.success(request, f"✅ Se cerraron {count} periodo(s) correctamente.")
    return redirect('periodo_list') 

# LISTAR
@login_required
def grado_list(request):
    centro = get_centro_activo(request)

    grados = Grado.objects.filter(
        nivel__centro=centro
    ).select_related('nivel')

    return render(request, 'academico/grado_list.html', {
        'grados': grados
    })


# CREAR
@login_required
def grado_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = GradoForm(request.POST)
        if form.is_valid():
            grado = form.save(commit=False)

            # Validación extra de seguridad
            if grado.nivel.centro != centro:
                return redirect('grado_list')

            grado.save()
            return redirect('grado_list')
    else:
        form = GradoForm()
        form.fields['nivel'].queryset = Nivel.objects.filter(centro=centro)

    return render(request, 'academico/grado_form.html', {
        'form': form,
        'accion': 'Crear'
    })


# EDITAR
@login_required
def grado_update(request, pk):
    centro = get_centro_activo(request)
    grado = get_object_or_404(
        Grado,
        pk=pk,
        nivel__centro=centro
    )

    if request.method == 'POST':
        form = GradoForm(request.POST, instance=grado)
        if form.is_valid():
            grado = form.save(commit=False)
            if grado.nivel.centro == centro:
                grado.save()
            return redirect('grado_list')
    else:
        form = GradoForm(instance=grado)
        form.fields['nivel'].queryset = Nivel.objects.filter(centro=centro)

    return render(request, 'academico/grado_form.html', {
        'form': form,
        'accion': 'Editar'
    })


# ELIMINAR
@login_required
def grado_delete(request, pk):
    grado = get_object_or_404(Grado, pk=pk)

    if request.method == 'POST':
        grado.delete()
        return JsonResponse({'success': True})

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })





@login_required
def seccion_list(request):
    centro = get_centro_activo(request)

    secciones = Seccion.objects.filter(
        grado__nivel__centro=centro
    ).select_related('grado', 'grado__nivel')

    return render(request, 'academico/seccion_list.html', {
        'secciones': secciones
    })


@login_required
def seccion_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = SeccionForm(request.POST)
        if form.is_valid():
            seccion = form.save(commit=False)

            if seccion.grado.nivel.centro != centro:
                return redirect('seccion_list')

            seccion.save()
            return redirect('seccion_list')
    else:
        form = SeccionForm()
        form.fields['grado'].queryset = Grado.objects.filter(
            nivel__centro=centro
        )

    return render(request, 'academico/seccion_form.html', {
        'form': form,
        'accion': 'Crear'
    })


@login_required
def seccion_update(request, pk):
    centro = get_centro_activo(request)
    seccion = get_object_or_404(
        Seccion,
        pk=pk,
        grado__nivel__centro=centro
    )

    if request.method == 'POST':
        form = SeccionForm(request.POST, instance=seccion)
        if form.is_valid():
            seccion = form.save(commit=False)
            if seccion.grado.nivel.centro == centro:
                seccion.save()
            return redirect('seccion_list')
    else:
        form = SeccionForm(instance=seccion)
        form.fields['grado'].queryset = Grado.objects.filter(
            nivel__centro=centro
        )

    return render(request, 'academico/seccion_form.html', {
        'form': form,
        'accion': 'Editar'
    })


@login_required
def seccion_delete(request, pk):
    seccion = get_object_or_404(Seccion, pk=pk)

    if request.method == 'POST':
        seccion.delete()
        return redirect('seccion_list')

    return redirect('seccion_list')




@login_required
def area_list(request):
    centro = get_centro_activo(request)

    areas = AreaCurricular.objects.filter(centro=centro)

    return render(request, 'academico/area_list.html', {
        'areas': areas
    })


@login_required
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
def area_delete(request, pk):
    area = get_object_or_404(AreaCurricular, pk=pk)

    if request.method == 'POST':
        area.delete()
        return redirect('area_list')

    return redirect('area_list')



@login_required
def asignatura_list(request):
    centro = get_centro_activo(request)

    asignaturas = Asignatura.objects.filter(
        centro=centro
    ).select_related('area')

    return render(request, 'academico/asignatura_list.html', {
        'asignaturas': asignaturas
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
def asignatura_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = AsignaturaForm(
            request.POST,
            centro=centro
        )

        if form.is_valid():
            asignatura = form.save(commit=False)
            asignatura.centro = centro   # 🔐 seguridad
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
def grado_asignatura_list(request):
    centro = get_centro_activo(request)

    relaciones = GradoAsignatura.objects.filter(
        grado__nivel__centro=centro,
        asignatura__centro=centro
    ).select_related(
        'grado',
        'grado__nivel',
        'asignatura'
    ).order_by(
        'grado__nivel__nombre',
        'grado__nombre',
        'asignatura__nombre'
    )

    return render(
        request,
        'academico/grado_asignatura_list.html',
        {
            'relaciones': relaciones
        }
    )



@login_required
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
def competencia_list(request):
    
    competencias = Competencia.objects.all().order_by('nombre')
    return render(request, 'academico/competencia_list.html', {
        'competencias': competencias
    })


@login_required
def competencia_create(request):
    form = CompetenciaForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect('competencia_list')

    return render(request, 'academico/competencia_form.html', {
        'form': form,
        'titulo': 'Nueva Competencia'
    })


@login_required
def competencia_update(request, pk):
    competencia = get_object_or_404(Competencia, pk=pk)
    form = CompetenciaForm(request.POST or None, instance=competencia)

    if form.is_valid():
        form.save()
        return redirect('competencia_list')

    return render(request, 'academico/competencia_form.html', {
        'form': form,
        'titulo': 'Editar Competencia'
    })


@login_required
def competencia_delete(request, pk):
    competencia = get_object_or_404(Competencia, pk=pk)

    if request.method == 'POST':
        competencia.delete()
        return redirect('competencia_list')

    return render(request, 'academico/competencia_confirm_delete.html', {
        'competencia': competencia
    })


from .models import AreaCompetencia
from .forms import AreaCompetenciaForm


@login_required
def area_competencia_list(request):
    relaciones = AreaCompetencia.objects.select_related(
        'area', 'competencia'
    )
    return render(request, 'academico/area_competencia_list.html', {
        'relaciones': relaciones
    })



@login_required
def area_competencia_create(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    # Todas las asignaturas del centro
    asignaturas = Asignatura.objects.filter(centro=centro)
    competencias = Competencia.objects.all()  # todas las competencias disponibles

    if request.method == 'POST':
        asignatura_id = request.POST.get('asignatura')
        competencias_ids = request.POST.getlist('competencias')
        pesos = request.POST.getlist('peso')

        if asignatura_id and competencias_ids and pesos:
            asignatura = get_object_or_404(Asignatura, id=asignatura_id)

            for comp_id, peso in zip(competencias_ids, pesos):
                comp = get_object_or_404(Competencia, id=comp_id)

                # Solo crear si no existe la relación
                AreaCompetencia.objects.get_or_create(
                    area=asignatura.area,
                    competencia=comp,
                    defaults={'peso': peso}
                )

            messages.success(request, "Competencias asignadas correctamente.")
            return redirect('area_competencia_list')

    return render(request, 'academico/area_competencia_form.html', {
        'asignaturas': asignaturas,
        'competencias': competencias,
    })




@login_required
def area_competencia_delete(request, pk):
    relacion = get_object_or_404(AreaCompetencia, pk=pk)

    if request.method == 'POST':
        relacion.delete()
        return redirect('area_competencia_list')

    return render(request, 'academico/area_competencia_confirm_delete.html', {
        'relacion': relacion
    })


from django.shortcuts import render, redirect, get_object_or_404
from .models import Periodo
from .forms import PeriodoForm



def periodo_list(request):
    centro = get_centro_activo(request)

    periodos = Periodo.objects.filter(
        centro=centro
    ).select_related('anio_escolar')

    return render(request, 'academico/periodo_list.html', {
        'periodos': periodos
    })


@login_required
def periodo_create(request):
    centro = get_centro_activo(request)
    if request.method == 'POST':
        form = PeriodoForm(request.POST, centro=centro)
        if form.is_valid():
            periodo = form.save(commit=False)
            periodo.centro = centro
            periodo.save()
            return redirect('periodo_list')
    else:
        form = PeriodoForm(centro=centro)

    return render(request, 'academico/periodo_form.html', {
        'form': form,
        'accion': 'Nuevo Período'
    })



@login_required
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
def periodo_delete(request, pk):
    centro = get_centro_activo(request)
    periodo = get_object_or_404(Periodo, pk=pk, centro=centro)

    periodo.delete()
    return JsonResponse({'success': True})


from django.shortcuts import render, redirect, get_object_or_404
from .models import DocenteMateria
from .forms import DocenteMateriaForm



def docentemateria_list(request):
    centro = get_centro_activo(request)

    asignaciones = DocenteMateria.objects.filter(
        docente__centro=centro
    ).select_related(
        'docente',
        'asignatura',
        'grado',
        'seccion',
        'anio_escolar'
    )

    return render(request, 'academico/docentemateria_list.html', {
   
        'asignaciones': asignaciones
    })


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

    return JsonResponse({'error': 'Método no permitido'}, status=405)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from administracion.models import AnioEscolar
from academico.forms import AnioEscolarForm


@login_required
def anio_escolar_list(request):
    centro = get_centro_activo(request)

    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')

    return render(request, 'academico/anio_escolar_list.html', {
        'anios': anios
    })


@login_required
def anio_escolar_create(request):
    centro = get_centro_activo(request)

    if request.method == 'POST':
        form = AnioEscolarForm(request.POST)
        if form.is_valid():
            anio = form.save(commit=False)
            anio.centro = centro

            # Solo un año activo por centro
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
    # VALIDAR PERÍODOS ABIERTOS
    # ====================================
    if Periodo.objects.filter(
        anio_escolar=anio,
        cerrado=False
    ).exists():

        messages.error(
            request,
            "No se puede cerrar el año escolar. Existen períodos abiertos."
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
            f"No se puede cerrar el año escolar. Existen {pendientes.count()} estudiantes pendientes."
        )

        return redirect('anio_escolar_list')

    # ====================================
    # CERRAR AÑO ESCOLAR
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
            f"Año escolar {anio.nombre} cerrado correctamente."
        )

    except Exception as e:

        messages.error(
            request,
            f"Error al cerrar el año escolar: {e}"
        )

    return redirect('anio_escolar_list')