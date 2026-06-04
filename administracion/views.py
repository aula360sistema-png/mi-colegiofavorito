from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)
from django.utils import timezone
from django.utils.crypto import get_random_string

from academico.models import (
    AreaCompetencia,
    Calificacion,
    DocenteMateria,
    Grado,
    Periodo,
    Seccion
)

from administracion.forms import (
    AdministrativoForm,
    AnioEscolarForm
)

from administracion.models import (
    Acta,
    Administrativo
)

from administracion.services.acta import generar_acta_estudiante

from core.decorators import (
    centro_required,
    role_required
)

from core.models import (
    AnioEscolar,
    CentroEducativo
)

from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from docentes.models import Docente

from estudiantes.models import (
    Estudiante,
    Inscripcion
)

from django.db import transaction
from usuarios.models import Usuario
from core.utils.centro import obtener_centro_del_usuario

from django.contrib import messages
from django.db.models import Count


@login_required
@role_required('director', 'secretaria', 'superadmin')
@centro_required
def dashboard_admin(request):
    user = request.user

    centro = request.centro

    anio_actual = (
        AnioEscolar.objects
        .filter(
            centro=centro,
            activo=True
        )
        .first()
    )

    if not anio_actual:

        messages.warning(
            request,
            "No hay año escolar activo."
        )

    total_docentes = Docente.objects.filter(
        centro=centro
    ).count()

    total_estudiantes = Estudiante.objects.filter(
        centro=centro
    ).count()

    total_grados = Grado.objects.filter(
        nivel__centro=centro
    ).count()

    total_secciones = Seccion.objects.filter(
        grado__nivel__centro=centro
    ).count()

    total_asignaciones = (
        DocenteMateria.objects.filter(
            docente__centro=centro,
            anio_escolar=anio_actual
        ).count()
        if anio_actual else 0
    )

    docentes_sin_asignacion = (
        Docente.objects.filter(
            centro=centro,
            estado='activo'
        )
        .exclude(
            docentemateria__anio_escolar=anio_actual
        )
        .count()
        if anio_actual else 0
    )

    estudiantes_inscritos = (
        Inscripcion.objects.filter(
            centro=centro,
            anio_escolar=anio_actual
        ).count()
        if anio_actual else 0
    )

    estudiantes_sin_inscripcion = (
        total_estudiantes - estudiantes_inscritos
    )

    estudiantes_por_grado = (
        Inscripcion.objects
        .filter(
            centro=centro,
            anio_escolar=anio_actual
        )
        .values('grado__nombre')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    docentes_por_nivel = (
        DocenteMateria.objects
        .filter(
            docente__centro=centro,
            anio_escolar=anio_actual
        )
        .values('grado__nivel__nombre')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    context = {
        'centro': centro,
        'anio_actual': anio_actual,

        'total_docentes': total_docentes,
        'total_estudiantes': total_estudiantes,
        'total_grados': total_grados,
        'total_secciones': total_secciones,
        'total_asignaciones': total_asignaciones,

        'docentes_sin_asignacion': docentes_sin_asignacion,
        'estudiantes_sin_inscripcion': estudiantes_sin_inscripcion,

        'estudiantes_por_grado': estudiantes_por_grado,
        'docentes_por_nivel': docentes_por_nivel,

        'es_director': request.user.rol == 'director',
        'es_secretaria': request.user.rol == 'secretaria',
    }

    return render(
        request,
        'administracion/dashboard.html',
        context
    )


from django.utils import timezone



@login_required
@role_required('director', 'superadmin')
@centro_required
def administrativo_create(request):

    centro = request.centro

    if request.method == 'POST':

        form = AdministrativoForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                admin = form.save(commit=False)

                admin.centro = centro
                admin.fecha_ingreso = timezone.now().date()

                cargo_form = form.cleaned_data['cargo']

                admin.cargo = cargo_form

                email_usuario = (
                    admin.correo_personal
                    or f"{admin.cedula}@colegio.com"
                )

                username_usuario = admin.cedula

                password = get_random_string(8)

                usuario = Usuario.objects.create_user(
                    username=username_usuario,
                    email=email_usuario,
                    password=password
                )

                usuario.rol = cargo_form
                usuario.save()

                admin.usuario = usuario

                admin.save()

            return render(
                request,
                'administracion/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password,
                    'centro': centro.nombre,
                    'cargo': admin.cargo
                }
            )

    else:

        form = AdministrativoForm()

    return render(
        request,
        'administracion/administrativo_form.html',
        {
            'form': form
        }
    )




from core.models import AnioEscolar
from estudiantes.models import Inscripcion

from core.utils.anio import obtener_anio_activo


@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def listado_personal(request):

    centro = request.centro
    tipo = request.GET.get('tipo')

    administrativos = []
    estudiantes = []

    # ================= ADMINISTRATIVOS =================
    if tipo == 'administrativo':

        administrativos = (
            Administrativo.objects
            .filter(centro=centro)
            .select_related('usuario')
        )

    # ================= ESTUDIANTES =================
    elif tipo == 'estudiante':

        anio_actual = obtener_anio_activo(centro)

        estudiantes = (
            Estudiante.objects
            .filter(centro=centro)
            .select_related('usuario')
        )

        # 🔥 Traer TODAS las inscripciones de una vez
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

        # 🔥 Relacionar sin hacer queries extra
        for e in estudiantes:

            inscripcion = inscripciones.get(e.id)

            e.grado_actual = (
                inscripcion.grado.nombre
                if inscripcion and inscripcion.grado
                else '—'
            )

            e.seccion_actual = (
                inscripcion.seccion.nombre
                if inscripcion and inscripcion.seccion
                else '—'
            )

    return render(
        request,
        'administracion/listado_personal.html',
        {
            'centro': centro,
            'tipo': tipo,
            'administrativos': administrativos,
            'estudiantes': estudiantes,
        }
    )


@login_required
@role_required('director', 'secretaria', 'superadmin')
def mantenimiento_home(request):
    user = request.user

    centro = user.administrativo.centro

    return render(request, 'administracion/mantenimiento.html', {
        'centro': centro
    })

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP




def redondear(valor):
    return float(Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))




@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def generar_boletines(request):
    if request.method != "POST":
        return redirect("administracion:dashboard_admin")

    centro = request.centro

    anio = obtener_anio_activo(centro)

    if not anio:
        messages.error(request, "No hay año escolar activo.")
        return redirect("administracion:dashboard_admin")

    # 🔒 Validar que TODOS los períodos estén cerrados
    if Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio,
        cerrado=False
    ).exists():
        messages.error(
            request,
            "❌ No se pueden generar boletines. Hay períodos abiertos."
        )
        return redirect("administracion:dashboard_admin")

    inscripciones = Inscripcion.objects.filter(
        centro=centro,
        anio_escolar=anio
    ).select_related("estudiante")

    creados = 0

    for inscripcion in inscripciones:
        acta, creada = generar_acta_estudiante(
            inscripcion=inscripcion,
            centro=centro,
            anio=anio,
            usuario=request.user
        )
        if creada:
            creados += 1

    messages.success(
        request,
        f"✅ Boletines oficiales generados correctamente ({creados})"
    )

    # ✅ RETORNO OBLIGATORIO
    return redirect("administracion:lista_boletines")

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from administracion.models import Acta


@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def ver_boletin_estudiante(request, acta_id):
    """
    Vista SOLO LECTURA del boletín oficial (Acta).
    No recalcula nada, solo muestra el snapshot guardado.
    """

    acta = get_object_or_404(Acta, id=acta_id, centro=request.centro)

    context = {
        "acta": acta,
        "datos": acta.datos,  # JSON ya construido
    }

    return render(request, "administracion/boletines/ver_boletin.html", context)

@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def lista_boletines(request):
    centro = request.centro

    actas = (
        Acta.objects
        .filter(centro=centro)
        .select_related('estudiante', 'grado', 'anio_escolar')
        .order_by('grado', 'seccion', 'estudiante__primer_apellido')
    )

    context = {
        "actas": actas
    }

    return render(request, "administracion/boletines/lista_boletines.html", context)

    



from core.models import AnioEscolar
from administracion.forms import AnioEscolarForm


@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def anio_escolar_list(request):
    centro = request.centro

    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')

    return render(request, 'academico/anio_escolar_list.html', {
        'anios': anios
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def anio_escolar_create(request):
    centro = request.centro

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
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def anio_escolar_update(request, pk):
    centro = request.centro 

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


from django.shortcuts import render
from administracion.models import Acta

@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def seguimiento_estudiantes(request):
    centro = request.centro

    actas_qs = (
    Acta.objects
    .select_related(
        "estudiante",
        "grado",
        "anio_escolar",
        "generado_por",
        "centro",
    )
    .order_by(
        "grado__nombre",
        "seccion",
        "estudiante__primer_apellido",
        "estudiante__primer_nombre",
    )
)

    actas = []

    for acta in actas_qs:
        datos = acta.datos or {}
        asignaturas = datos.get("asignaturas", [])

        # 🧮 Calcular promedio general desde los PF
        pfs = [
            a["pf"]
            for a in asignaturas
            if a.get("pf") is not None
        ]

        promedio_general = (
            round(sum(pfs) / len(pfs), 2)
            if pfs else None
        )

        actas.append({
            "estudiante": acta.estudiante,
            "grado": acta.grado,
            "seccion": acta.seccion,
            "promedio": promedio_general,
            "acta_id": acta.id
        })

    return render(
        request,
        "administracion/seguimiento_estudiantes.html",
        {
            "actas": actas
        }
    )





@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def seguimiento_estudiante(request, estudiante_id):
    centro = request.centro
    if not centro:
        return redirect('seleccionar_centro')

    actas = (
        Acta.objects
        .filter(
            centro=centro,
            estudiante_id=estudiante_id
        )
        .select_related('anio_escolar', 'grado')
        .order_by('-anio_escolar__nombre')
    )

    estudiante = actas.first().estudiante if actas else None

    return render(request, "administracion/seguimiento_estudiante.html", {
        "estudiante": estudiante,
        "actas": actas
    })




from django.shortcuts import get_object_or_404, render
from administracion.models import Acta

@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def imprimir_boletin_acta(request, acta_id):
    centro = request.centro
    acta = get_object_or_404(Acta, id=acta_id, centro=centro)

    datos = acta.datos  # SNAPSHOT OFICIAL (JSON)

    return render(
        request,
        "administracion/boletines/boletin_imprimible.html",
        {
            "acta": acta,
            "datos": datos,
        }
    )
