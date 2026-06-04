from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect

from academico.models import DocenteMateria
from core.decorators import centro_required
from .models import Estudiante
from usuarios.models import Usuario
from core.models import CentroEducativo


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Estudiante, Inscripcion
from .forms import EstudianteForm, InscripcionForm
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


@login_required
def estudiante_create(request):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('seleccionar_centro')

    if request.method == 'POST':
        form = EstudianteForm(request.POST)
        if form.is_valid():
            estudiante = form.save(commit=False)
            estudiante.centro = centro

            # 🔐 Crear usuario automático
            password = get_random_string(8)

            usuario = Usuario.objects.create_user(
                username=estudiante.matricula,
                email=f"{estudiante.matricula}@colegio.com",
                password=password
            )

            # 🏷 Asignar rol estudiante
            usuario.rol = 'estudiante'
            usuario.save()

            # 🔗 Vincular usuario con estudiante
            estudiante.usuario = usuario
            estudiante.save()

            return render(request, 'estudiantes/credenciales.html', {
                'usuario': usuario.username,
                'password': password
            })
    else:
        form = EstudianteForm()

    return render(request, 'estudiantes/estudiante_form.html', {'form': form})


@login_required
def estudiante_update(request, pk):
    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    if request.method == 'POST':
        form = EstudianteForm(request.POST, instance=estudiante)
        if form.is_valid():
            form.save()
            return redirect('estudiante_list')
    else:
        form = EstudianteForm(instance=estudiante)

    return render(request, 'estudiantes/estudiante_form.html', {'form': form})


@login_required
def estudiante_detail(request, pk):
    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        pk=pk,
        centro=centro
    )

    inscripciones = Inscripcion.objects.filter(estudiante=estudiante)

    return render(
        request,
        'estudiantes/estudiante_detail.html',
        {
            'estudiante': estudiante,
            'inscripciones': inscripciones
        }
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

@login_required
def inscribir_estudiante(request, estudiante_id):
    centro = get_centro_activo(request)

    estudiante = get_object_or_404(
        Estudiante,
        id=estudiante_id,
        centro=centro
    )

    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.estudiante = estudiante
            inscripcion.centro = centro
            inscripcion.save()
            return redirect('estudiante_detail', pk=estudiante.id)
    else:
        form = InscripcionForm()

    return render(
        request,
        'estudiantes/inscripcion_form.html',
        {'form': form, 'estudiante': estudiante}
    )




@login_required
@centro_required
def estudiante_list(request):
    centro = request.centro

    anio_activo = AnioEscolar.objects.filter(
        centro=centro,
        activo=True
    ).first()

    estudiantes = Estudiante.objects.filter(
        centro=centro
    ).prefetch_related(
        Prefetch(
            'inscripcion_set',
            queryset=Inscripcion.objects.filter(anio_escolar=anio_activo),
            to_attr='inscripcion_actual'
        )
    )

    return render(
        request,
        'estudiantes/estudiante_list.html',
        {
            'estudiantes': estudiantes,
            'centro': centro,
            'anio_activo': anio_activo
        }
    )

from django.http import JsonResponse
from academico.models import Seccion
from django.contrib.auth.decorators import login_required


@login_required
def ajax_cargar_secciones(request):
    grado_id = request.GET.get('grado')

    secciones = Seccion.objects.filter(
        grado_id=grado_id
    ).values('id', 'nombre')

    return JsonResponse(list(secciones), safe=False)


@login_required
def inscribir_estudiante_avanzado(request, estudiante_id):
    print("🟢 Entrando a inscribir_estudiante_avanzado")
    print("➡️ Usuario:", request.user)
    print("➡️ Estudiante ID recibido:", estudiante_id)

    centro = get_centro_activo(request)
    print("➡️ Centro activo desde sesión:", centro)

    if not centro:
        print("❌ No hay centro activo en sesión")
        return redirect('seleccionar_centro')

    estudiante = get_object_or_404(
        Estudiante,
        id=estudiante_id,
        centro=centro
    )
    print("✅ Estudiante encontrado:", estudiante)

    # 🔒 Año escolar activo
    try:
        anio_escolar = AnioEscolar.objects.get(
            centro=centro,
            activo=True
        )
        print("✅ Año escolar activo:", anio_escolar)
    except AnioEscolar.DoesNotExist:
        print("❌ No existe año escolar activo para este centro")
        messages.error(
            request,
            'No hay un año escolar activo para este centro'
        )
        return redirect('estudiante_detail', pk=estudiante.id)

    # ❌ Validar doble inscripción
    ya_inscrito = Inscripcion.objects.filter(
        estudiante=estudiante,
        anio_escolar=anio_escolar
    ).exists()

    print("➡️ ¿Ya está inscrito en este año?:", ya_inscrito)

    if ya_inscrito:
        print("⚠️ Inscripción duplicada detectada")
        messages.warning(
            request,
            'Este estudiante ya está inscrito en el año escolar activo'
        )
        return redirect('estudiante_detail', pk=estudiante.id)

    if request.method == 'POST':
        print("📨 Request POST recibido")
        print("➡️ POST data:", request.POST)

        form = InscripcionAvanzadaForm(
            request.POST,
            centro=centro
        )

        print("➡️ Formulario válido?:", form.is_valid())

        if form.is_valid():
            inscripcion = form.save(commit=False)

            print("➡️ Grado seleccionado:", inscripcion.grado)
            print("➡️ Sección seleccionada:", inscripcion.seccion)

            inscripcion.estudiante = estudiante
            inscripcion.centro = centro
            inscripcion.anio_escolar = anio_escolar

            inscripcion.save()
            print("✅ Inscripción guardada con ID:", inscripcion.id)

            messages.success(
                request,
                'Estudiante inscrito correctamente'
            )
            return redirect('estudiante_detail', pk=estudiante.id)
        else:
            print("❌ Errores del formulario:", form.errors)

    else:
        print("📄 Request GET – mostrando formulario")
        form = InscripcionAvanzadaForm(centro=centro)

    print("🟢 Renderizando template de inscripción avanzada")

    return render(
        request,
        'estudiantes/inscripcion_avanzada_form.html',
        {
            'form': form,
            'estudiante': estudiante,
            'anio_escolar': anio_escolar
        }
    )




@login_required
def inscripcion_asignaturas(request, inscripcion_id):
    centro = get_centro_activo(request)
    if not centro:
        return redirect('seleccionar_centro')

    inscripcion = get_object_or_404(
        Inscripcion,
        id=inscripcion_id,
        centro=centro
    )

    asignaciones = DocenteMateria.objects.filter(
        grado=inscripcion.grado,
        seccion=inscripcion.seccion,
        anio_escolar=inscripcion.anio_escolar
    ).select_related('asignatura', 'docente')

    print("INSCRIPCIÓN:", inscripcion.id)
    print("GRADO:", inscripcion.grado_id)
    print("SECCIÓN:", inscripcion.seccion_id)
    print("AÑO:", inscripcion.anio_escolar_id)

    print("DOCENTE MATERIA DISPONIBLES:")
    print(DocenteMateria.objects.values(
        'grado_id', 'seccion_id', 'anio_escolar_id'
    ))

    return render(
        request,
        'estudiantes/inscripcion_asignaturas.html',
        {
            'inscripcion': inscripcion,
            'asignaciones': asignaciones
        }
    )
