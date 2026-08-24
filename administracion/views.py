from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Sum, Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)
from django.utils import timezone
from django.utils.crypto import get_random_string
from django_ratelimit.decorators import ratelimit

from academico.models import (
    Calificacion,
    DocenteMateria,
    Grado,
    Periodo,
    PeriodoAnio,
    Seccion
)

from academico.services.periodos import abrir_periodos_anio, sincronizar_periodos_anio, sincronizar_periodos_centro

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
from core.services import modulo_activo

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


def obtener_metricas_dashboard(centro):
    """Métricas del dashboard cacheadas ~60s para no recalcular en cada request.

    Se guardan como valores planos (lists/dicts) para que sean serializables
    en LocMemCache y Redis.
    """
    from django.core.cache import cache
    from core.cache_utils import ttl

    clave = f'dashboard:{centro.id}:{obtener_version_dashboard(centro.id)}'
    metricas = cache.get(clave)
    if metricas is not None:
        return metricas

    anio_actual = (
        AnioEscolar.objects
        .filter(
            centro=centro,
            activo=True
        )
        .first()
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
        centro=centro
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

    estudiantes_por_grado = list(
        Inscripcion.objects
        .filter(
            centro=centro,
            anio_escolar=anio_actual
        )
        .values('grado__nombre')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    docentes_por_nivel = list(
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
    caja_activa = modulo_activo(centro.id, 'caja')
    if anio_actual:
        sincronizar_periodos_anio(anio_actual)
        periodos_qs = PeriodoAnio.objects.filter(
            anio_escolar=anio_actual,
            periodo__es_completivo=False,
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

        if caja_activa:
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
            # Plan sin caja: sin recaudo que mostrar.
            total_recaudado = 0
            total_recibos = 0
            ultimos_pagos = []
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

    metricas = {
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
        'caja_activa': caja_activa,
    }

    cache.set(clave, metricas, timeout=ttl('CACHE_TTL_CORTO'))
    return metricas


def obtener_version_dashboard(centro_id):
    from core.cache_utils import obtener_version
    return obtener_version(f'dashboard:{centro_id}')


def invalidar_dashboard(centro_id):
    from core.cache_utils import invalidar_dominio
    invalidar_dominio(f'dashboard:{centro_id}')


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
@centro_required
def dashboard_admin(request):
    user = request.user

    centro = request.centro

    metricas = obtener_metricas_dashboard(centro)

    return render(
        request,
        'administracion/dashboard.html',
        {
            'centro': centro,
            'es_director': request.user.rol == 'director',
            'es_secretaria': request.user.rol == 'secretaria',
            **metricas,
        }
    )


from django.utils import timezone



@login_required
@role_required('director', 'admin', 'superadmin')
@centro_required
def administrativo_create(request):

    centro = request.centro

    if request.method == 'POST':

        form = AdministrativoForm(request.POST, request.FILES)

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
                usuario.debe_cambiar_password = True
                usuario.save()

                admin.usuario = usuario

                admin.save()

            return render(
                request,
                'usuarios/credenciales.html',
                {
                    'usuario': usuario.username,
                    'password': password,
                    'centro': centro.nombre,
                    'cargo': admin.cargo,
                    'tipo_nombre': 'Administrativo',
                    'tipo_slug': 'administrativo',
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
@role_required('director', 'secretaria', 'admin', 'superadmin')
def listado_personal(request):

    centro = request.centro
    tipo = request.GET.get('tipo')
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    if tipo not in ('administrativo', 'estudiante'):
        tipo = ''

    stats = obtener_stats_personal(centro)

    # ================= ADMINISTRATIVOS =================
    if tipo == 'administrativo':

        administrativos = (
            Administrativo.objects
            .filter(centro=centro)
            .select_related('usuario')
        )

        if q:
            administrativos = administrativos.filter(
                Q(primer_nombre__icontains=q) |
                Q(segundo_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(segundo_apellido__icontains=q) |
                Q(cedula__icontains=q)
            )

        if estado:
            administrativos = administrativos.filter(estado=estado)

        administrativos = administrativos.order_by('primer_apellido', 'primer_nombre')

        paginator = Paginator(administrativos, 10)
        page_obj = paginator.get_page(request.GET.get('page'))

        return render(
            request,
            'administracion/listado_personal.html',
            {
                'centro': centro,
                'tipo': tipo,
                'administrativos': page_obj.object_list,
                'page_obj': page_obj,
                'q': q,
                'estado': estado,
                'stats': stats,
            }
        )

    # ================= ESTUDIANTES =================
    if tipo == 'estudiante':

        estudiantes = (
            Estudiante.objects
            .filter(centro=centro)
            .select_related('usuario')
        )

        if q:
            estudiantes = estudiantes.filter(
                Q(matricula__icontains=q) |
                Q(primer_nombre__icontains=q) |
                Q(segundo_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(segundo_apellido__icontains=q)
            )

        if estado:
            estudiantes = estudiantes.filter(estado=estado)

        estudiantes = estudiantes.order_by('primer_apellido', 'primer_nombre')

        paginator = Paginator(estudiantes, 10)
        page_obj = paginator.get_page(request.GET.get('page'))

        # 🔥 Traer TODAS las inscripciones de una vez (solo página actual)
        inscripciones = {
            i.estudiante_id: i
            for i in (
                Inscripcion.objects
                .filter(
                    centro=centro,
                    anio_escolar=obtener_anio_activo(centro),
                    estudiante_id__in=[e.id for e in page_obj.object_list]
                )
                .select_related('grado', 'seccion')
            )
        }

        # 🔥 Relacionar sin hacer queries extra
        for e in page_obj.object_list:

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
                'estudiantes': page_obj.object_list,
                'page_obj': page_obj,
                'q': q,
                'estado': estado,
                'stats': stats,
            }
        )

    # ================= SIN SELECCIÓN =================
    return render(
        request,
        'administracion/listado_personal.html',
        {
            'centro': centro,
            'tipo': tipo,
            'administrativos': [],
            'estudiantes': [],
            'q': q,
            'estado': estado,
            'stats': stats,
        }
    )


@login_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
@centro_required
def mantenimiento_home(request):
    centro = request.centro

    from academico.models import (
        AreaCurricular,
        Asignatura,
        Competencia,
        GradoAsignatura,
        Grado,
        Nivel,
        Periodo,
        PeriodoAnio,
        Seccion,
    )

    anio_activo = obtener_anio_activo(centro)
    if anio_activo:
        sincronizar_periodos_anio(anio_activo)

    conteos = {
        'anios': AnioEscolar.objects.filter(centro=centro).count(),
        'niveles': Nivel.objects.filter(centro=centro).count(),
        'grados': Grado.objects.filter(nivel__centro=centro).count(),
        'secciones': Seccion.objects.filter(centro=centro).count(),
        'areas': AreaCurricular.objects.filter(centro=centro).count(),
        'asignaturas': Asignatura.objects.filter(centro=centro).count(),
        'grados_asignaturas': GradoAsignatura.objects.filter(
            grado__nivel__centro=centro
        ).count(),
        'competencias': Competencia.objects.filter(nivel__centro=centro).count(),
        'periodos': Periodo.objects.filter(centro=centro).count(),
        'docentematerias': DocenteMateria.objects.filter(
            anio_escolar__centro=centro
        ).count(),
    }

    return render(request, 'administracion/mantenimiento.html', {
        'centro': centro,
        'conteos': conteos,
        'todos_cerrados': (
            anio_activo is not None and
            PeriodoAnio.objects.filter(anio_escolar=anio_activo).exists() and
            not PeriodoAnio.objects.filter(
                anio_escolar=anio_activo,
                cerrado=False
            ).exists()
        ),
    })

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP




def redondear(valor):
    return float(Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))



@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
@ratelimit(key='ip', rate='50/h', method='POST', block=True)
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
    if PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False,
        periodo__es_completivo=False
    ).exists():
        messages.error(
            request,
            "❌ No se pueden generar boletines. Hay períodos abiertos."
        )
        return redirect("administracion:dashboard_admin")

    if not PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=True,
        periodo__es_completivo=False
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
@role_required('director', 'admin', 'superadmin')
@ratelimit(key='ip', rate='20/h', method='POST', block=True)
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

    completivo_abierto = PeriodoAnio.objects.filter(
        anio_escolar=anio,
        periodo__es_completivo=True,
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


def obtener_stats_personal(centro):
    """Conteos de la pantalla de personal, cacheados por dominio.

    Dependen de la versión de estudiantes (Estudiante) y de personal
    (Administrativo), ambas invalidadas por sus respectivas señales.
    """
    from core.cache_utils import obtener_o_generar, obtener_version, ttl

    clave = (
        f'stats_personal:{centro.id}:'
        f'{obtener_version(f"estudiantes:{centro.id}")}:'
        f'{obtener_version(f"personal:{centro.id}")}'
    )
    return obtener_o_generar(
        clave,
        lambda: _obtener_stats_personal_sql(centro),
        version=1,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


def _obtener_stats_personal_sql(centro):
    return {
        'admin_total': Administrativo.objects.filter(centro=centro).count(),
        'admin_activos': Administrativo.objects.filter(centro=centro, estado='activo').count(),
        'admin_inactivos': Administrativo.objects.filter(centro=centro, estado='inactivo').count(),
        'est_total': Estudiante.objects.filter(centro=centro).count(),
        'est_activos': Estudiante.objects.filter(centro=centro, estado='activo').count(),
        'est_retirados': Estudiante.objects.filter(centro=centro, estado='retirado').count(),
        'est_egresados': Estudiante.objects.filter(centro=centro, estado='egresado').count(),
    }


def actas_del_centro(centro):
    """Boletines (actas) del centro, cacheados por dominio.

    Es la consulta base de la lista de boletines: la vista filtra y
    pagina en memoria para no re-consultar la BD por cada combinación
    de filtros. Se invalida con la señal de `Acta`.
    """
    from core.cache_utils import obtener_o_generar, obtener_version, ttl

    clave = (
        f'actas:{centro.id}:'
        f'{obtener_version(f"actas:{centro.id}")}'
    )
    return obtener_o_generar(
        clave,
        lambda: list(
            Acta.objects.filter(centro=centro).select_related(
                'estudiante', 'grado', 'anio_escolar'
            ).order_by('grado', 'seccion', 'estudiante__primer_apellido')
        ),
        version=1,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def reportes(request):
    centro = request.centro

    metricas = obtener_metricas_reportes(centro)

    # --- Consulta de matrícula por año / grado / sección -------------
    anios = AnioEscolar.objects.filter(
        centro=centro
    ).order_by('-fecha_inicio')
    # Los grados son un catálogo compartido; los del centro son aquellos
    # vinculados a alguna de sus secciones.
    grados = (
        Grado.objects
        .filter(secciones__centro=centro)
        .distinct()
        .order_by('orden')
    )

    anio_actual = obtener_anio_activo(centro)
    sel_anio = request.GET.get('anio') or (
        str(anio_actual.id) if anio_actual else ''
    )
    sel_grado = request.GET.get('grado', '')
    sel_seccion = request.GET.get('seccion', '')

    inscripciones = []
    if sel_anio and sel_grado:
        filtros = {
            'anio_escolar_id': sel_anio,
            'grado_id': sel_grado,
        }
        if sel_seccion:
            filtros['seccion_id'] = sel_seccion

        inscripciones = list(
            Inscripcion.objects
            .filter(centro=centro, **filtros)
            .select_related(
                'estudiante',
                'grado',
                'seccion',
                'anio_escolar',
            )
            .order_by(
                'estudiante__primer_apellido',
                'estudiante__primer_nombre',
            )
        )

    secciones_del_grado = (
        Seccion.objects.filter(
            centro=centro,
            grados__id=sel_grado,
        ).order_by('nombre')
        if sel_grado else Seccion.objects.none()
    )

    return render(request, 'administracion/reportes.html', {
        'centro': centro,
        **metricas,
        'anios': anios,
        'grados': grados,
        'secciones_del_grado': secciones_del_grado,
        'sel_anio': str(sel_anio or ''),
        'sel_grado': sel_grado,
        'sel_seccion': sel_seccion,
        'inscripciones': inscripciones,
    })


def obtener_metricas_reportes(centro):
    """Agregados de la pantalla de reportes cacheados.

    Las claves dependen de la versión de estructura (grados/secciones/
    periodos) y de estudiantes (matrícula/inscripciones), así que se
    invalidan con las señales existentes.
    """
    from core.cache_utils import (
        invalidar_dominio,
        obtener_o_generar,
        obtener_version,
        ttl,
    )

    clave = (
        f'reportes:{centro.id}:'
        f'{obtener_version(f"estructura:{centro.id}")}:'
        f'{obtener_version(f"estudiantes:{centro.id}")}'
    )
    return obtener_o_generar(
        clave,
        lambda: _obtener_metricas_reportes_sql(centro),
        version=1,
        timeout=ttl('CACHE_TTL_MEDIO'),
    )


def _obtener_metricas_reportes_sql(centro):
    anio_actual = obtener_anio_activo(centro)

    matricula_por_grado = list(
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('grado__nombre', 'seccion__nombre')
        .annotate(total=Count('id'))
        .order_by('grado__orden', 'seccion__nombre')
        if anio_actual else []
    )

    matricula_por_anio = list(
        Inscripcion.objects
        .filter(centro=centro)
        .values('anio_escolar__nombre')
        .annotate(total=Count('id'))
        .order_by('-anio_escolar__fecha_inicio')
    )

    estudiantes_por_estado = list(
        Estudiante.objects
        .filter(centro=centro)
        .values('estado')
        .annotate(total=Count('id'))
    )

    estados_academicos = list(
        Inscripcion.objects
        .filter(centro=centro, anio_escolar=anio_actual)
        .values('estado_final')
        .annotate(total=Count('id'))
        if anio_actual else []
    )

    total_matricula_activa = sum(r['total'] for r in matricula_por_grado)
    total_estudiantes = Estudiante.objects.filter(centro=centro).count()
    total_estados_academicos = sum(r['total'] for r in estados_academicos)

    return {
        'anio_actual': anio_actual,
        'matricula_por_grado': matricula_por_grado,
        'matricula_por_anio': matricula_por_anio,
        'estudiantes_por_estado': estudiantes_por_estado,
        'estados_academicos': estados_academicos,
        'total_matricula_activa': total_matricula_activa,
        'total_estudiantes': total_estudiantes,
        'total_estados_academicos': total_estados_academicos,
    }


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
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
@role_required('director', 'secretaria', 'admin', 'superadmin')
def lista_boletines(request):

    centro = request.centro

    actas = actas_del_centro(centro)

    # 🔥 filtros GET (en memoria sobre la lista base cacheada)
    q = request.GET.get("q", "").strip()
    anio_id = request.GET.get("anio")
    estado = request.GET.get("estado")

    if q:
        ql = q.lower()
        actas = [
            a for a in actas
            if (
                ql in (a.estudiante.primer_nombre or '').lower()
                or ql in (a.estudiante.segundo_nombre or '').lower()
                or ql in (a.estudiante.primer_apellido or '').lower()
                or ql in (a.estudiante.segundo_apellido or '').lower()
                or ql in (a.estudiante.matricula or '').lower()
            )
        ]

    if anio_id:
        actas = [a for a in actas if a.anio_escolar_id == int(anio_id)]

    if estado:
        actas = [
            a for a in actas
            if a.datos.get('estado_final') == estado
        ]

    resumen = {
        'total': len(actas),
        'aprobado': sum(
            1 for a in actas if a.datos.get('estado_final') == 'aprobado'
        ),
        'reprobado': sum(
            1 for a in actas if a.datos.get('estado_final') == 'reprobado'
        ),
        'recuperacion': sum(
            1 for a in actas if a.datos.get('estado_final') == 'recuperacion'
        ),
    }
    resumen['pendiente'] = (
        resumen['total']
        - resumen['aprobado']
        - resumen['reprobado']
        - resumen['recuperacion']
    )

    paginator = Paginator(actas, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        "actas": page_obj.object_list,
        "page_obj": page_obj,
        "anios": AnioEscolar.objects.filter(centro=centro).order_by('-fecha_inicio'),
        "filtro_anio": anio_id,
        "filtro_estado": estado,
        "q": q,
        "resumen": resumen,
        "es_director": request.user.rol == 'director',
    }

    return render(request, "administracion/boletines/lista_boletines.html", context)

    



from core.models import AnioEscolar
from administracion.forms import AnioEscolarForm


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
def anio_escolar_list(request):
    centro = request.centro

    from academico.services import estructura

    anios = estructura.anios_escolares(centro)

    return render(request, 'academico/anio_escolar_list.html', {
        'anios': anios
    })


@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
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
            abrir_periodos_anio(anio)
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
            abrir_periodos_anio(anio)
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
@role_required('director', 'secretaria', 'admin', 'superadmin')
def seguimiento_estudiantes(request):
    centro = request.centro

    q = request.GET.get('q', '').strip()
    grado_id = request.GET.get('grado', '').strip()

    actas_qs = (
        Acta.objects
        .filter(centro=centro)
        .select_related(
            "estudiante",
            "grado",
            "anio_escolar",
            "generado_por",
            "centro",
        )
        .order_by(
            "-anio_escolar__fecha_inicio",
            "estudiante_id",
        )
    )

    if q:
        actas_qs = actas_qs.filter(
            Q(estudiante__primer_nombre__icontains=q) |
            Q(estudiante__segundo_nombre__icontains=q) |
            Q(estudiante__primer_apellido__icontains=q) |
            Q(estudiante__segundo_apellido__icontains=q) |
            Q(estudiante__matricula__icontains=q)
        )

    if grado_id:
        actas_qs = actas_qs.filter(grado_id=grado_id)

    # Una fila por estudiante: el acta más reciente (último promedio)
    unicos = {}
    for acta in actas_qs:
        if acta.estudiante_id not in unicos:
            unicos[acta.estudiante_id] = acta

    actas_unico = list(unicos.values())

    total_estudiantes = len(actas_unico)

    def _estado_promedio(p):
        if p is None:
            return None
        if p >= 70:
            return 'aprobado'
        if p >= 60:
            return 'recuperacion'
        return 'reprobado'

    resumen = {'aprobado': 0, 'recuperacion': 0, 'reprobado': 0, 'sin_promedio': 0}
    for acta in actas_unico:
        datos = acta.datos or {}
        asignaturas = datos.get("asignaturas", [])
        pfs = [a["pf"] for a in asignaturas if a.get("pf") is not None]
        promedio = round(sum(pfs) / len(pfs), 2) if pfs else None
        estado = _estado_promedio(promedio)
        if estado is None:
            resumen['sin_promedio'] += 1
        else:
            resumen[estado] += 1

    actas_unico.sort(
        key=lambda a: (
            a.grado.nombre,
            a.seccion or '',
            a.estudiante.primer_apellido,
            a.estudiante.primer_nombre,
        )
    )

    paginator = Paginator(actas_unico, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    grados = set(a.grado for a in actas_unico)
    grados = sorted(grados, key=lambda g: g.nombre)

    actas = []

    for acta in page_obj.object_list:
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
            "anio": acta.anio_escolar.nombre,
            "promedio": promedio_general,
            "acta_id": acta.id
        })

    return render(
        request,
        "administracion/seguimiento_estudiantes.html",
        {
            "actas": actas,
            "page_obj": page_obj,
            "grados": grados,
            "total_estudiantes": total_estudiantes,
            "resumen": resumen,
            "q": q,
            "grado_seleccionado": grado_id,
        }
    )





@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
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
        .order_by('-anio_escolar__fecha_inicio')
    )

    estudiante = actas.first().estudiante if actas else None

    filas = []
    for acta in actas:
        datos = acta.datos or {}
        asignaturas = datos.get("asignaturas", [])
        pfs = [a["pf"] for a in asignaturas if a.get("pf") is not None]
        promedio = round(sum(pfs) / len(pfs), 2) if pfs else None

        if promedio is None:
            estado = 'sin_promedio'
        elif promedio >= 70:
            estado = 'aprobado'
        elif promedio >= 60:
            estado = 'recuperacion'
        else:
            estado = 'reprobado'

        filas.append({
            "acta": acta,
            "anio": acta.anio_escolar.nombre,
            "grado": acta.grado,
            "seccion": acta.seccion or '—',
            "promedio": promedio,
            "estado": estado,
        })

    return render(request, "administracion/seguimiento_estudiante.html", {
        "estudiante": estudiante,
        "actas": filas,
        "total_boletines": len(filas),
    })




from django.shortcuts import get_object_or_404, render
from administracion.models import Acta

@login_required
@centro_required
@role_required('director', 'secretaria', 'admin', 'superadmin')
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
