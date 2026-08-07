from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
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

from administracion.services.boletin import (
    construir_boletin_estudiante,
    enriquecer_boletin_para_vista,
    resultado_completivo_estudiante
)
from core.decorators import (
    centro_required,
    role_required
)

from core.models import (
    AnioEscolar,
    CentroEducativo,
    ConfiguracionCentro
)

from core.utils.anio import obtener_anio_activo
from core.utils.session import get_centro_activo

from caja.models import Pago
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

    # ================= MÉTRICAS ACADÉMICAS DEL AÑO ACTIVO =================
    if anio_actual:
        periodos_qs = Periodo.objects.filter(
            centro=centro,
            anio_escolar=anio_actual,
            es_completivo=False,
        )
        periodos_abiertos = periodos_qs.filter(cerrado=False).count()
        periodos_cerrados = periodos_qs.filter(cerrado=True).count()
        total_periodos = periodos_abiertos + periodos_cerrados
        porcentaje_periodos_cerrados = (
            round(periodos_cerrados * 100 / total_periodos)
            if total_periodos else 0
        )

        actas_generadas = Acta.objects.filter(
            centro=centro,
            anio_escolar=anio_actual,
        ).count()
        porcentaje_actas_generadas = (
            round(actas_generadas * 100 / estudiantes_inscritos)
            if estudiantes_inscritos else 0
        )

        promedio_agregado = Inscripcion.objects.filter(
            centro=centro,
            anio_escolar=anio_actual,
            promedio_final__isnull=False,
        ).aggregate(promedio=Avg('promedio_final'))['promedio']
        promedio_general = (
            round(float(promedio_agregado), 2)
            if promedio_agregado is not None else None
        )

        estado_labels = dict(Inscripcion.ESTADO_FINALES)
        estado_colores = {
            'aprobado': '#10b981',
            'reprobado': '#ef4444',
            'recuperacion': '#f59e0b',
            'retirado': '#94a3b8',
            'pendiente': '#cbd5e1',
            'sin_calificacion': '#e2e8f0',
        }
        estudiantes_por_estado = [
            {
                'estado': item['estado_final'],
                'label': estado_labels.get(
                    item['estado_final'], item['estado_final']
                ),
                'total': item['total'],
                'color': estado_colores.get(
                    item['estado_final'], '#e2e8f0'
                ),
            }
            for item in Inscripcion.objects
            .filter(centro=centro, anio_escolar=anio_actual)
            .values('estado_final')
            .annotate(total=Count('id'))
        ]

        pagos_anio = Pago.objects.filter(
            centro=centro,
            fecha__range=(anio_actual.fecha_inicio, anio_actual.fecha_fin),
        )
        total_recaudado = float(
            pagos_anio.aggregate(total=Sum('monto'))['total'] or 0
        )
        total_recibos = pagos_anio.count()
        ultimos_pagos = list(
            pagos_anio
            .select_related('estudiante', 'concepto')
            .order_by('-fecha', '-id')[:5]
        )
    else:
        periodos_abiertos = 0
        periodos_cerrados = 0
        total_periodos = 0
        porcentaje_periodos_cerrados = 0
        actas_generadas = 0
        porcentaje_actas_generadas = 0
        promedio_general = None
        estudiantes_por_estado = []
        total_recaudado = 0
        total_recibos = 0
        ultimos_pagos = []

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

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
        'estudiantes_por_estado': estudiantes_por_estado,

        'periodos_abiertos': periodos_abiertos,
        'periodos_cerrados': periodos_cerrados,
        'porcentaje_periodos_cerrados': porcentaje_periodos_cerrados,
        'actas_generadas': actas_generadas,
        'porcentaje_actas_generadas': porcentaje_actas_generadas,
        'promedio_general': promedio_general,
        'nota_minima': nota_minima,

        'total_recaudado': total_recaudado,
        'total_recibos': total_recibos,
        'ultimos_pagos': ultimos_pagos,

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

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

    # 🔒 validar períodos cerrados (se ignoran los completivos)
    if Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio,
        cerrado=False,
        es_completivo=False
    ).exists():
        messages.error(
            request,
            "❌ No se pueden generar boletines. Hay períodos abiertos."
        )
        return redirect("administracion:dashboard_admin")

    if not Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio,
        cerrado=True,
        es_completivo=False
    ).exists():
        messages.error(
            request,
            "❌ No hay períodos cerrados para generar boletines."
        )
        return redirect("administracion:lista_boletines")

    inscripciones = Inscripcion.objects.filter(
        centro=centro,
        anio_escolar=anio
    ).select_related("estudiante", "grado", "seccion")

    creados = 0
    actualizados = 0
    sin_periodos = 0

    for inscripcion in inscripciones:

        # 🔥 1. CONSTRUIR BOLETÍN COMPLETO (motor real)
        try:
            boletin = construir_boletin_estudiante(
                inscripcion=inscripcion,
                centro=centro,
                anio=anio
            )
        except ValueError:
            sin_periodos += 1
            continue

        # 🔥 2. EXTRAER PROMEDIO GENERAL
        asignaturas = boletin.get("asignaturas", [])

        promedios = [
            a["pf"]
            for a in asignaturas
            if a.get("pf") is not None
        ]

        promedio_general = (
            sum(promedios) / len(promedios)
            if promedios else None
        )
        tiene_materia_reprobada = any(
            (a.get("pf") or 0) < nota_minima
            for a in asignaturas
            if a.get("pf") is not None
        )

        # 🔥 3. DEFINIR ESTADO ACADÉMICO
        if not promedios:
            estado = "sin_calificacion"
        elif tiene_materia_reprobada:
            estado = "recuperacion"
        elif promedio_general >= nota_minima:
            estado = "aprobado"
        else:
            estado = "reprobado"

        # 🔥 4. ACTUALIZAR INSCRIPCIÓN (estado operativo)
        inscripcion.promedio_final = promedio_general
        inscripcion.estado_final = estado
        inscripcion.save()

        # 🔥 5. AGREGAR ESTADO AL BOLETÍN (IMPORTANTE PARA FILTROS)
        boletin["estado_final"] = estado
        boletin["promedio_general"] = promedio_general

        # 🔥 6. GENERAR / ACTUALIZAR ACTA (snapshot oficial)
        acta, creada = Acta.objects.update_or_create(
            centro=centro,
            anio_escolar=anio,
            estudiante=inscripcion.estudiante,
            defaults={
                "grado": inscripcion.grado,
                "seccion": str(inscripcion.seccion),
                "datos": boletin,
                "generado_por": request.user
            }
        )

        if creada:
            creados += 1
        else:
            actualizados += 1

    messages.success(
        request,
        f"✅ Boletines procesados correctamente. Nuevos: {creados}, "
        f"Actualizados: {actualizados}."
        + (f" Sin períodos: {sin_periodos}." if sin_periodos else "")
    )

    return redirect("administracion:lista_boletines")


@login_required
@centro_required
@role_required('director', 'superadmin')
def cerrar_completivo(request):
    """
    Cierra el completivo del año activo: los estudiantes en estado
    'recuperacion' aprueban si superaron TODAS las asignaturas reprobadas
    dentro del (los) período(s) de completivo cerrado(s).
    """

    if request.method != "POST":
        return redirect("administracion:lista_boletines")

    centro = request.centro
    anio = obtener_anio_activo(centro)

    if not anio:
        messages.error(request, "No hay año escolar activo.")
        return redirect("administracion:lista_boletines")

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

    completivo_abierto = Periodo.objects.filter(
        centro=centro,
        anio_escolar=anio,
        es_completivo=True,
        cerrado=False
    ).exists()

    if completivo_abierto:
        messages.error(
            request,
            "❌ El período de completivo está abierto. Ciérralo antes de procesar."
        )
        return redirect("administracion:lista_boletines")

    inscripciones = Inscripcion.objects.filter(
        centro=centro,
        anio_escolar=anio,
        estado_final='recuperacion'
    ).select_related("estudiante")

    aprobados = 0
    reprobados = 0
    sin_completivo = 0

    for inscripcion in inscripciones:

        resultado = resultado_completivo_estudiante(
            inscripcion,
            centro,
            anio,
            nota_minima
        )

        if resultado is None:
            sin_completivo += 1
            continue

        inscripcion.estado_final = (
            'aprobado' if resultado["aprobado"] else 'reprobado'
        )
        inscripcion.save()

        if resultado["aprobado"]:
            aprobados += 1
        else:
            reprobados += 1

        acta = Acta.objects.filter(
            centro=centro,
            anio_escolar=anio,
            estudiante=inscripcion.estudiante
        ).first()

        if acta:
            datos = dict(acta.datos or {})
            datos["estado_final"] = inscripcion.estado_final
            datos["completivo"] = resultado
            acta.datos = datos
            acta.save(update_fields=["datos"])

    messages.success(
        request,
        f"✅ Completivo procesado: {aprobados} aprobados, "
        f"{reprobados} reprobados, {sin_completivo} sin completivo."
    )

    return redirect("administracion:lista_boletines")

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from administracion.models import Acta


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def reportes(request):
    centro = request.centro

    anio_actual = obtener_anio_activo(centro)

    # Matrícula por grado + sección (año activo)
    matricula_por_grado = (
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('grado__nombre', 'seccion__nombre')
        .annotate(total=Count('id'))
        .order_by('grado__orden', 'seccion__nombre')
        if anio_actual else []
    )

    # Matrícula por año escolar
    matricula_por_anio = (
        Inscripcion.objects
        .filter(centro=centro)
        .values('anio_escolar__nombre')
        .annotate(total=Count('id'))
        .order_by('-anio_escolar__fecha_inicio')
    )

    # Estudiantes por estado general
    estudiantes_por_estado = (
        Estudiante.objects
        .filter(centro=centro)
        .values('estado')
        .annotate(total=Count('id'))
    )

    # Estados académicos de la matrícula activa
    estados_academicos = (
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('estado_final')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    return render(request, 'administracion/reportes.html', {
        'centro': centro,
        'anio_actual': anio_actual,
        'matricula_por_grado': matricula_por_grado,
        'matricula_por_anio': matricula_por_anio,
        'estudiantes_por_estado': estudiantes_por_estado,
        'estados_academicos': estados_academicos,
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def ver_boletin_estudiante(request, acta_id):
    """
    Vista SOLO LECTURA del boletín oficial (Acta).
    No recalcula nada, solo muestra el snapshot guardado.
    """

    acta = get_object_or_404(Acta, id=acta_id, centro=request.centro)

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=request.centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

    context = {
        "acta": acta,
        "datos": enriquecer_boletin_para_vista(acta.datos),
        "nota_minima": nota_minima,
    }

    return render(request, "administracion/boletines/ver_boletin.html", context)

@login_required
@centro_required
@role_required('director', 'secretaria', 'superadmin')
def lista_boletines(request):

    centro = request.centro

    actas = Acta.objects.filter(
        centro=centro
    ).select_related(
        'estudiante', 'grado', 'anio_escolar'
    )

    # 🔥 filtros GET
    anio_id = request.GET.get("anio")
    estado = request.GET.get("estado")

    if anio_id:
        actas = actas.filter(anio_escolar_id=anio_id)

    if estado:
        actas = actas.filter(datos__estado_final=estado)

    actas = actas.order_by(
        'grado',
        'seccion',
        'estudiante__primer_apellido'
    )
  
    context = {
        "actas": actas,
        "anios": AnioEscolar.objects.filter(centro=centro).order_by('-fecha_inicio'),
        "filtro_anio": anio_id,
        "filtro_estado": estado,
        "es_director": request.user.rol == 'director',
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
        return redirect('core:seleccionar_centro')

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

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

    tipo_nivel = "primaria"
    if acta.grado and acta.grado.nivel_id:
        tipo_nivel = acta.grado.nivel.tipo

    plantillas = {
        "inicial": "administracion/boletines/boletin_imprimible_inicial.html",
        "secundaria": "administracion/boletines/boletin_imprimible_secundaria.html",
    }
    plantilla = plantillas.get(tipo_nivel, "administracion/boletines/boletin_imprimible_primaria.html")

    return render(
        request,
        plantilla,
        {
            "acta": acta,
            "datos": enriquecer_boletin_para_vista(datos),
            "nota_minima": nota_minima,
            "tipo_nivel": tipo_nivel,
        }
    )
