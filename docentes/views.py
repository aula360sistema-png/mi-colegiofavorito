from collections import defaultdict
import json
import logging

from django.db import models
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.core.paginator import Paginator
# Create your views here.
# docentes/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy

from academico.models import DocenteMateria, GradoAsignatura
from administracion.models import Acta
from core.decorators import ajax_required, centro_required, role_required
from core.utils import centro
from core.utils.anio import obtener_anio_activo
from academico.services.periodos import sincronizar_periodos_anio
from .models import AsignacionDocente, Docente
from .forms import DocenteForm
from django.contrib.auth.decorators import login_required

from core.models import CentroEducativo
from .utils import generar_password
from core.utils.session import get_centro_activo
from datetime import date
# Listado de docentes
from django.db.models import Q

logger = logging.getLogger(__name__)

@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docente_list(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('core:seleccionar_centro')

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    from .services import docentes_del_centro

    docentes = docentes_del_centro(centro)

    stats = {
        'total': len(docentes),
        'activos': sum(1 for d in docentes if d.estado == 'activo'),
        'inactivos': sum(1 for d in docentes if d.estado == 'inactivo'),
    }

    if q:
        ql = q.lower()
        docentes = [
            d for d in docentes
            if ql in (d.primer_nombre or '').lower()
            or ql in (d.segundo_nombre or '').lower()
            or ql in (d.primer_apellido or '').lower()
            or ql in (d.segundo_apellido or '').lower()
            or ql in (d.cedula or '').lower()
        ]

    if estado:
        docentes = [d for d in docentes if d.estado == estado]

    paginator = Paginator(docentes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'docentes': page_obj.object_list,
        'centro': centro,
        'q': q,
        'estado': estado,
        'stats': stats,
    }

    return render(
        request,
        'docentes/docente_list.html',
        context
    )
# Crear nuevo docente

from usuarios.models import Usuario

from .utils import generar_password



from usuarios.models import Usuario
from django.utils.crypto import get_random_string

@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docente_create(request):
    centro = get_centro_activo(request)

    if not centro:
        return redirect('core:seleccionar_centro')

    if request.method == 'POST':
        form = DocenteForm(request.POST, request.FILES)

        if form.is_valid():

            docente = form.save(commit=False)
            docente.centro = centro

            password = get_random_string(8)

            usuario = Usuario.objects.create_user(
                username=docente.cedula,
                email=docente.correo_personal or f"{docente.cedula}@colegio.com",
                password=password
            )

            usuario.rol = 'docente'
            usuario.debe_cambiar_password = True
            usuario.save()

            docente.usuario = usuario
            docente.save()

            return render(
                request,
                'usuarios/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password,
                    'centro': centro.nombre,
                    'tipo_nombre': 'Docente',
                    'tipo_slug': 'docente',
                }
            )
    else:
        form = DocenteForm()

    return render(
        request,
        'docentes/docente_form.html',
        {
            'form': form
        }
    )


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docente_update(request, pk):
    centro = get_centro_activo(request)

    docente = get_object_or_404(
        Docente,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':

        form = DocenteForm(
            request.POST,
            request.FILES,
            instance=docente
        )

        if form.is_valid():
            form.save()
            return redirect('docente_detail', pk=docente.pk)

    else:
        form = DocenteForm(instance=docente)

    return render(
        request,
        'docentes/docente_form.html',
        {
            'form': form,
            'docente': docente
        }
    )

# Eliminar docente
@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
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

from datetime import date

from datetime import date

@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def docente_detail(request, pk):
    centro = get_centro_activo(request)

    docente = get_object_or_404(
        Docente,
        pk=pk,
        centro=centro
    )

    asignaciones = (
        DocenteMateria.objects
        .filter(docente=docente)
        .select_related(
            'asignatura',
            'grado',
            'seccion',
            'anio_escolar'
        )
        .order_by(
            '-anio_escolar__fecha_inicio',
            'grado__nombre',
            'asignatura__nombre'
        )
    )

    anios_servicio = (
        date.today().year -
        docente.fecha_ingreso.year
    )

    anios_datos = []
    anios_agrupados = {}
    for a in asignaciones:
        anios_agrupados.setdefault(a.anio_escolar, []).append(a)

    for anio, items in anios_agrupados.items():
        paginator = Paginator(items, 5)
        page_number = request.GET.get(f'pagina_{anio.id}')
        page_obj = paginator.get_page(page_number)
        anios_datos.append({
            'anio': anio,
            'page_obj': page_obj,
        })

    return render(
        request,
        'docentes/docente_detail.html',
        {
            'docente': docente,
            'asignaciones': asignaciones,
            'anios_datos': anios_datos,
            'anios_servicio': anios_servicio,
        }
    )

from django.shortcuts import render, get_object_or_404
from academico.models import Calificacion, Competencia, DocenteMateria, PeriodoAnio
from docentes.models import Docente

from core.models import AnioEscolar

from django.contrib.auth.decorators import login_required

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from academico.models import DocenteMateria, Periodo

from core.models import AnioEscolar

@login_required
@role_required('docente')
@centro_required
def dashboard_docente(request):
    docente = request.user.docente
    centro = request.centro

    anio_actual = obtener_anio_activo(centro)

    if not anio_actual:
        messages.error(request, "No hay año escolar activo.")
        datos = {
            'periodos': [],
            'total_asignaciones': 0,
            'asignaciones_con_notas': 0,
            'asignaciones_completas': 0,
            'asignaciones': [],
            'total_estudiantes': 0,
        }
    else:
        from .services import datos_dashboard_docente

        datos = datos_dashboard_docente(docente, anio_actual)

    return render(request, 'docentes/dashboard.html', {
        'docente': docente,
        'anio': anio_actual,
        'periodos': datos['periodos'],
        'total_asignaciones': datos['total_asignaciones'],
        'asignaciones_con_notas': datos['asignaciones_con_notas'],
        'asignaciones_completas': datos['asignaciones_completas'],
        'asignaciones': datos['asignaciones'],
        'total_estudiantes': datos['total_estudiantes'],
    })







from estudiantes.models import Inscripcion

@login_required
@role_required('docente')
def docente_estudiantes(request, asignacion_id):

    asignacion = get_object_or_404(
        DocenteMateria,
        id=asignacion_id,
        docente=request.user.docente
    )

    q = request.GET.get('q', '').strip()

    inscripciones = (
        Inscripcion.objects.filter(
            grado=asignacion.grado,
            seccion=asignacion.seccion,
            anio_escolar=asignacion.anio_escolar
        )
        .select_related('estudiante')
        .order_by(
            'estudiante__primer_apellido',
            'estudiante__primer_nombre'
        )
    )

    if q:
        inscripciones = inscripciones.filter(
            Q(estudiante__matricula__icontains=q) |
            Q(estudiante__primer_nombre__icontains=q) |
            Q(estudiante__segundo_nombre__icontains=q) |
            Q(estudiante__primer_apellido__icontains=q) |
            Q(estudiante__segundo_apellido__icontains=q)
        )

    return render(
        request,
        'docentes/estudiantes.html',
        {
            'asignacion': asignacion,
            'inscripciones': inscripciones,
            'q': q,
            'total_estudiantes': inscripciones.count(),
        }
    )


from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


@login_required
@role_required('docente')
@ajax_required
def guardar_notas_ajax(request, asignacion_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False})

    logger.debug('Petición AJAX de notas recibida')
    try:
        data = json.loads(request.body)
    except Exception as e:
        logger.warning('Error decodificando JSON de notas: %s', e)
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)
    logger.debug('Datos de notas: %s', data)

    asignacion = get_object_or_404(
        DocenteMateria,
        id=asignacion_id,
        docente__usuario=request.user
    )

    estudiantes_data = data.get('estudiantes') or [{
        'inscripcion': data['inscripcion'],
        'notas': data['notas']
    }]

    guardadas = 0
    for est in estudiantes_data:
        inscripcion = Inscripcion.objects.filter(id=est['inscripcion']).first()
        if not inscripcion:
            continue

        for item in est['notas']:
            if item.get('nota') in ('', None):
                continue

            Calificacion.objects.update_or_create(
                inscripcion=inscripcion,
                asignatura=asignacion.asignatura,
                competencia_id=item['competencia'],
                periodo_id=item['periodo'],
                defaults={'nota': item['nota'], 'origen': 'docente'},
            )
            guardadas += 1

    return JsonResponse({'ok': True, 'guardadas': guardadas})


@login_required
@role_required('docente')
@centro_required
def calificar_tabla(request, asignacion_id):
    centro = request.centro
    if not centro:
        return redirect('core:seleccionar_centro')

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

    sincronizar_periodos_anio(asignacion.anio_escolar)

    periodos = Periodo.objects.filter(
        estados__anio_escolar=asignacion.anio_escolar,
        estados__activo=True
    ).order_by('orden')
    periodos_cerrados = set(
        PeriodoAnio.objects.filter(
            anio_escolar=asignacion.anio_escolar,
            cerrado=True
        ).values_list('periodo_id', flat=True)
    )
    todos_cerrados = bool(periodos) and all(
        p.id in periodos_cerrados for p in periodos
    )




    # Catálogo MINERD: todas las asignaturas del nivel usan las mismas
    # competencias al calificar.
    competencias = Competencia.objects.filter(
        nivel=asignacion.grado.nivel,
        activo=True
    ).order_by('orden', 'id')

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
            for c in competencias:
                for p in periodos:
                    if p.id in periodos_cerrados:
                     continue  

                    campo = f"nota_{ins.id}_{c.id}_{p.id}"
                    nota = request.POST.get(campo)

                    if nota not in (None, ''):
                        Calificacion.objects.update_or_create(
                            inscripcion=ins,
                            asignatura=asignacion.asignatura,
                            competencia=c,
                            periodo=p,
                            defaults={'nota': nota, 'origen': 'docente'}
                        )

        messages.success(request, 'Calificaciones guardadas')
        return redirect('calificar_tabla', asignacion_id=asignacion.id)

    return render(request, 'docentes/calificar_tabla.html', {
        'asignacion': asignacion,
        'inscripciones': inscripciones,
        'competencias': competencias,
        'periodos': periodos,
        'notas': notas, 
        'todos_cerrados' : todos_cerrados,
        'periodos_cerrados': periodos_cerrados,
    })
