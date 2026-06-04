from collections import defaultdict
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
# Create your views here.
# docentes/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy

from administracion.models import Acta
from core.decorators import ajax_required, centro_required, role_required
from core.utils.anio import obtener_anio_activo
from .models import AsignacionDocente, Docente
from .forms import DocenteForm
from django.contrib.auth.decorators import login_required

from core.models import CentroEducativo
from .utils import generar_password
from core.utils.session import get_centro_activo

# Listado de docentes
@login_required
def docente_list(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('seleccionar_centro')

    docentes = Docente.objects.filter(centro=centro)

    return render(
        request,
        'docentes/docente_list.html',
        {
            'docentes': docentes,
            'centro': centro
        }
    )

# Crear nuevo docente

from usuarios.models import Usuario

from .utils import generar_password



from usuarios.models import Usuario
from django.utils.crypto import get_random_string

@login_required
def docente_create(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('seleccionar_centro')

    if request.method == 'POST':
        form = DocenteForm(request.POST)
        if form.is_valid():
            docente = form.save(commit=False)
            docente.centro = centro

            # 🔐 Crear usuario automático
            password = get_random_string(8)

            usuario = Usuario.objects.create_user(
                username=docente.cedula,
                email=docente.correo_personal or f"{docente.cedula}@colegio.com",
                password=password
            )

            # 🏷 Asignar rol automáticamente
            usuario.rol = 'docente'
            usuario.save()
            
            docente.usuario = usuario
            docente.save()

            print("✅ Usuario creado:", usuario.username)
            print("🔐 Password:", password)

            return render(request, 'docentes/credenciales.html', {
                'usuario': usuario.username,
                'password': password
            })
    else:
        form = DocenteForm()

    return render(request, 'docentes/docente_form.html', {'form': form})


# Editar docente
@login_required
def docente_update(request, pk):
    centro = get_centro_activo(request)

    docente = get_object_or_404(
        Docente,
        pk=pk,
        centro=centro  # 🔒 seguridad
    )

    if request.method == 'POST':
        form = DocenteForm(request.POST, instance=docente)
        if form.is_valid():
            form.save()
            return redirect('docente_list')
    else:
        form = DocenteForm(instance=docente)

    return render(request, 'docentes/docente_form.html', {'form': form})

# Eliminar docente
@login_required
def docente_delete(request, pk):
    centro = get_centro_activo(request)

    docente = get_object_or_404(
        Docente,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        docente.delete()
        return redirect('docente_list')

    return render(
        request,
        'docentes/docente_confirm_delete.html',
        {'docente': docente}
    )

# Ver detalle de docente
@login_required
def docente_detail(request, pk):
    centro = get_centro_activo(request)

    docente = get_object_or_404(
        Docente,
        pk=pk,
        centro=centro
    )

    return render(request, 'docentes/docente_detail.html', {'docente': docente})




from django.shortcuts import render, get_object_or_404
from academico.models import AreaCompetencia, Calificacion, Competencia, DocenteMateria
from docentes.models import Docente

from core.models import AnioEscolar

from django.contrib.auth.decorators import login_required

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from academico.models import DocenteMateria, Periodo

from core.models import AnioEscolar

@login_required
def dashboard_docente2(request):
    docente = request.user.docente
    if request.user.rol != 'docente':
        return redirect('usuarios:logout')
    print("request", request.session)
    centro = get_centro_activo(request)

    anio = obtener_anio_activo(centro)
 

    asignaciones = DocenteMateria.objects.filter(
        docente=docente,
        anio_escolar=anio
    ).select_related(
        'asignatura',
        'grado',
        'seccion'
    )

    periodos = Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio,
        activo=True
    ).order_by('orden')

    total_asignaciones = asignaciones.count()

    asignaciones_con_notas = Acta.objects.filter(
        docente_materia__in=asignaciones,
        datos__isnull=False
    ).values('docente_materia').distinct().count()

    asignaciones_completas = Acta.objects.filter(
        docente_materia__in=asignaciones,
        completo=True  # o tu lógica de PF
    ).values('docente_materia').distinct().count()

    return render(request, 'docentes/dashboard.html', {
        'docente': docente,
        'anio': anio,
        'asignaciones': asignaciones,
        'periodos': periodos,
        
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q



@login_required
@role_required('docente')
@centro_required
def dashboard_docente(request):
    

    docente = request.user.docente
    centro = request.centro

    anio_actual = obtener_anio_activo(centro)

    if not anio_actual:
        messages.error(request, "No hay año escolar activo.")

    asignaciones_qs = DocenteMateria.objects.filter(
        docente=docente,
        anio_escolar=anio_actual
    ).select_related(
        'asignatura',
        'grado',
        'seccion'
    )

    periodos = Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio_actual,
        activo=True
    ).order_by('orden')

    total_asignaciones = asignaciones_qs.count()
    asignaciones_con_notas = 0
    asignaciones_completas = 0

    asignaciones = []

    for a in asignaciones_qs:

        actas = Acta.objects.filter(
            centro=centro,
            anio_escolar=anio_actual,
            grado=a.grado,
            seccion=a.seccion
        )

        estado = "pendiente"

        if actas.exists():
            estado = "progreso"

            completas = True

            for acta in actas:
                datos = acta.datos or {}
                asignaturas = datos.get("asignaturas", [])
                pfs = [
                    x.get("pf")
                    for x in asignaturas
                    if x.get("pf") is not None
                ]
                if not asignaturas or len(pfs) != len(asignaturas):
                    completas = False
                    break

            if completas:
                estado = "completo"

        if estado in ["progreso", "completo"]:
            asignaciones_con_notas += 1
        if estado == "completo":
            asignaciones_completas += 1

        asignaciones.append({
            "obj": a,
            "estado": estado
        })

    return render(request, 'docentes/dashboard.html', {
        'docente': docente,
        'anio': anio_actual,
        'periodos': periodos,
        'total_asignaciones': total_asignaciones,
        'asignaciones_con_notas': asignaciones_con_notas,
        'asignaciones_completas': asignaciones_completas,
        'asignaciones': asignaciones,
    })







from estudiantes.models import Inscripcion

@login_required
def docente_estudiantes(request, asignacion_id):
    asignacion = DocenteMateria.objects.get(
        id=asignacion_id,
        docente=request.user.docente
    )

    inscripciones = Inscripcion.objects.filter(
        grado=asignacion.grado,
        seccion=asignacion.seccion,
        anio_escolar=asignacion.anio_escolar
    ).select_related('estudiante')

    return render(request, 'docentes/estudiantes.html', {
        'asignacion': asignacion,
        'inscripciones': inscripciones
    })



from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


@login_required
@ajax_required
def guardar_notas_ajax(request, asignacion_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False})
    

    print("🔥 AJAX LLEGÓ")
    data = json.loads(request.body)
    print("📦 DATA:", data)

    asignacion = get_object_or_404(
        DocenteMateria,
        id=asignacion_id,
        docente__usuario=request.user
    )

    inscripcion = get_object_or_404(
        Inscripcion,
        id=data['inscripcion']
    )
    periodos = Periodo.objects.filter(
 #   centro=request.user.centro,
    anio_escolar=asignacion.anio_escolar,
    activo=True
)

  


    for item in data['notas']:
        if item['nota'] in ('', None):
            continue

        Calificacion.objects.update_or_create(
            inscripcion=inscripcion,
            asignatura=asignacion.asignatura,
            competencia_id=item['competencia'],
            periodo_id=item['periodo'],
            defaults={'nota': item['nota']},
       
        )

    return JsonResponse({'ok': True})


@login_required
@role_required('docente')
@centro_required
def calificar_tabla(request, asignacion_id):
    centro = request.centro
    if not centro:
        return redirect('seleccionar_centro')

    asignacion = get_object_or_404(
        DocenteMateria,
        id=asignacion_id,
        docente__usuario=request.user
    )

    inscripciones = Inscripcion.objects.filter(
        grado=asignacion.grado,
        seccion=asignacion.seccion,
        centro=centro,
        anio_escolar=asignacion.anio_escolar
    ).select_related('estudiante')

    periodos = Periodo.objects.filter(
        centro=centro,
        anio_escolar=asignacion.anio_escolar,
        activo=True
    ).order_by('orden')
    todos_cerrados = (
    periodos.exists() and
    not periodos.filter(cerrado=False).exists()
)




    area_competencias = AreaCompetencia.objects.filter(
        area=asignacion.asignatura.area
    ).select_related('competencia')

    # 🔥 NOTAS PRECARGADAS (ESTRUCTURA LIMPIA)
    notas = defaultdict(lambda: defaultdict(dict))

    calificaciones = Calificacion.objects.filter(
        asignatura=asignacion.asignatura,
        inscripcion__in=inscripciones,
        periodo__in=periodos
    )

    for c in calificaciones:
        notas[c.inscripcion_id][c.competencia_id][c.periodo_id] = c.nota

    # GUARDAR
    if request.method == 'POST':
        for ins in inscripciones:
            for ac in area_competencias:
                for p in periodos:
                    if p.cerrado:
                     continue  

                    campo = f"nota_{ins.id}_{ac.competencia.id}_{p.id}"
                    nota = request.POST.get(campo)

                    if nota not in (None, ''):
                        Calificacion.objects.update_or_create(
                            inscripcion=ins,
                            asignatura=asignacion.asignatura,
                            competencia=ac.competencia,
                            periodo=p,
                            defaults={'nota': nota}
                        )

        messages.success(request, 'Calificaciones guardadas')
        return redirect('calificar_tabla', asignacion_id=asignacion.id)

    return render(request, 'docentes/calificar_tabla.html', {
        'asignacion': asignacion,
        'inscripciones': inscripciones,
        'area_competencias': area_competencias,
        'periodos': periodos,
        'notas': notas, 
        'todos_cerrados' : todos_cerrados,
        
    })
