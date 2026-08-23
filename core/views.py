import logging

from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.contrib import messages

logger = logging.getLogger(__name__)

from core.decorators import role_required
from .models import CentroEducativo, ConfiguracionCentro, UsuarioCentro
from core.utils.centro import obtener_centro_del_usuario

# Create your views here.
from django.shortcuts import render



from django.shortcuts import redirect

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import CentroEducativo
from .forms import CentroEducativoForm, ConfiguracionCentroForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import CentroEducativo
from .forms import CentroEducativoForm

from academico.services.estructura_minerd import (
    cambiar_estructura_minerd,
    crear_estructura_minerd,
)


def custom_404_view(request, exception):
    if request.user.is_authenticated:
        return redirect('core:home')
    return redirect('usuarios:login')



@login_required
def home(request):
    user = request.user

    # 🔐 Admin Django
    if user.is_superuser:
      #  return redirect('/admin/')
        if not request.session.get('centro_id'):
            return redirect('core:seleccionar_centro')
        return redirect('administracion:dashboard_admin')

    # 🎓 DOCENTE
    if user.rol == 'docente':
        return redirect('dashboard_docente')

    # 🎒 ESTUDIANTE
    if user.rol == 'estudiante':
        return redirect('estudiante_inicio')

    # 👪 TUTOR
    if user.rol == 'tutor':
        return redirect('tutores:tutor_inicio')

    # 💵 CAJERO → módulo de caja
    if user.rol == 'cajero':
        from core.services import modulo_activo
        if modulo_activo(request.session.get('centro_id'), 'caja'):
            return redirect('caja:caja_inicio')
        messages.warning(
            request,
            'El módulo de caja no está activo para tu centro. '
            'Contacta al administrador.'
        )
        return redirect('usuarios:logout')

    # 🏫 DIRECTOR / SECRETARIA → ya tienen centro
    if user.rol in ['director', 'secretaria']:
        return redirect('administracion:dashboard_admin')

    # 🔥 ADMIN / SUPERADMIN → debe elegir centro (si no tiene)
    if user.rol in ('admin', 'superadmin'):
        if not request.session.get('centro_id'):
            return redirect('core:seleccionar_centro')
        return redirect('administracion:dashboard_admin')

    # 🚪 fallback
    return redirect('usuarios:logout')


@login_required
def seleccionar_centro(request):
    # Los miembros ya pertenecen a un centro: no eligen, se les asigna.
    if request.user.rol in ['director', 'secretaria', 'cajero', 'docente', 'estudiante', 'tutor']:
        centro = obtener_centro_del_usuario(request)
        if centro:
            request.session['centro_id'] = centro.id
            request.session.modified = True
            return redirect('core:home')

    if request.method == "POST":
        centro_id = request.POST.get("centro_id")

        request.session['centro_id'] = centro_id
        request.session.modified = True   # 🔴 CLAVE

        return redirect('core:home')  # o dashboard según rol

    centros = CentroEducativo.objects.all()
    return render(request, 'core/seleccionar_centro.html', {
        'centros': centros
    })



# core/views.py

@login_required
def dashboard(request):
    centro_id = request.session.get('centro_id')

    # Si no hay centro seleccionado, forzar selección
    if not centro_id:
        return redirect('core:seleccionar_centro')

    try:
        centro = CentroEducativo.objects.get(id=centro_id)
    except CentroEducativo.DoesNotExist:
        del request.session['centro_id']
        return redirect('core:seleccionar_centro')

    return render(
        request,
        'core/dashboard.html',
        {
            'centro': centro
        }
    )





# =========================
# LISTAR CENTROS
# =========================
@login_required
def centro_list(request):

    if request.user.rol != 'superadmin':
        return redirect('core:home')

    from .services import centros_listado

    centros = centros_listado()

    return render(request, 'core/centro_list.html', {
        'centros': centros
    })


# =========================
# CREAR CENTRO
# =========================
@login_required
@role_required('superadmin')
def centro_create(request):

    

    if request.method == 'POST':
        form = CentroEducativoForm(request.POST)

        if form.is_valid():
            centro = form.save()
            crear_estructura_minerd(
                centro,
                [form.cleaned_data['nivel']]
            )
            return redirect('core:centro_list')

    else:
        form = CentroEducativoForm()

    return render(request, 'core/centro_form.html', {
        'form': form,
        'accion': 'Crear'
    })


# =========================
# EDITAR CENTRO
# =========================
@login_required
@role_required('superadmin')
def centro_update(request, pk):

   

    centro = get_object_or_404(CentroEducativo, pk=pk)

    if request.method == 'POST':
        form = CentroEducativoForm(
            request.POST,
            instance=centro
        )

        if form.is_valid():
            resultado = cambiar_estructura_minerd(
                centro,
                form.cleaned_data['nivel'],
            )
            if resultado['status'] == 'bloqueado':
                form.add_error(
                    'nivel',
                    'No se puede cambiar el nivel porque el nivel anterior '
                    'tiene registros (inscripciones, actas, asignaciones). '
                    'Este centro se mantiene con su nivel actual.'
                )
            else:
                form.save()
                return redirect('core:centro_list')

    else:
        form = CentroEducativoForm(instance=centro)

    return render(request, 'core/centro_form.html', {
        'form': form,
        'accion': 'Editar'
    })


# =========================
# ELIMINAR CENTRO
# =========================
@login_required
@role_required('superadmin')
def centro_delete(request, pk):

    

    centro = get_object_or_404(CentroEducativo, pk=pk)

    centro.delete()

    return redirect('core:centro_list')


@login_required
@role_required('director', 'superadmin')
def configuracion_centro(request):

    centro_id = request.session.get('centro_id')

    if not centro_id:
        return redirect('core:seleccionar_centro')

    centro = get_object_or_404(
        CentroEducativo,
        id=centro_id
    )

    configuracion, created = ConfiguracionCentro.objects.get_or_create(
        centro=centro
    )

    if request.method == 'POST':

        form = ConfiguracionCentroForm(
            request.POST,
            instance=configuracion
        )

        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada.')
            return redirect('core:configuracion_centro')

    else:
        form = ConfiguracionCentroForm(instance=configuracion)

    return render(request, 'core/configuracion_centro.html', {
        'centro': centro,
        'form': form,
    })


# =========================
# PERMISOS POR PAGINA
# =========================

@login_required
@role_required('superadmin')
def permiso_pagina_list(request):
    from .models import PermisoPagina
    permisos = PermisoPagina.objects.prefetch_related('roles_permitidos', 'usuarios_permitidos').all()
    q = request.GET.get('q', '').strip()
    if q:
        permisos = permisos.filter(url_name__icontains=q)
    return render(request, 'core/permiso_pagina_list.html', {
        'permisos': permisos,
        'q': q,
    })


@login_required
@role_required('superadmin')
def permiso_pagina_create(request):
    from .models import PermisoPagina
    from .forms import PermisoPaginaForm

    if request.method == 'POST':
        form = PermisoPaginaForm(request.POST)
        if form.is_valid():
            permiso = form.save()
            from core.cache_utils import borrar
            borrar(f'perm_mw:{permiso.url_name}')
            borrar(f'perm_page:{permiso.url_name}')
            messages.success(request, f'Permiso para "{permiso.url_name}" creado.')
            return redirect('core:permiso_pagina_list')
    else:
        form = PermisoPaginaForm()

    return render(request, 'core/permiso_pagina_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
@role_required('superadmin')
def permiso_pagina_update(request, pk):
    from .models import PermisoPagina
    from .forms import PermisoPaginaForm

    permiso = get_object_or_404(PermisoPagina, pk=pk)

    # Capturar ANTES de is_valid(): el _post_clean del ModelForm muta la
    # instancia en memoria y old_url saldría con el valor nuevo.
    old_url = permiso.url_name

    if request.method == 'POST':
        form = PermisoPaginaForm(request.POST, instance=permiso)
        if form.is_valid():
            form.save()
            from core.cache_utils import borrar
            borrar(f'perm_mw:{old_url}')
            borrar(f'perm_page:{old_url}')
            if permiso.url_name != old_url:
                borrar(f'perm_mw:{permiso.url_name}')
                borrar(f'perm_page:{permiso.url_name}')
            messages.success(request, f'Permiso para "{permiso.url_name}" actualizado.')
            return redirect('core:permiso_pagina_list')
    else:
        form = PermisoPaginaForm(instance=permiso)

    return render(request, 'core/permiso_pagina_form.html', {
        'form': form,
        'accion': 'Editar',
    })


@login_required
@role_required('superadmin')
def permiso_pagina_delete(request, pk):
    from .models import PermisoPagina

    permiso = get_object_or_404(PermisoPagina, pk=pk)

    if request.method == 'POST':
        from core.cache_utils import borrar
        url_name = permiso.url_name
        permiso.delete()
        borrar(f'perm_mw:{url_name}')
        borrar(f'perm_page:{url_name}')
        messages.success(request, f'Permiso para "{url_name}" eliminado.')
        return redirect('core:permiso_pagina_list')

    return render(request, 'core/permiso_pagina_confirm_delete.html', {
        'permiso': permiso,
    })


# =========================
# APARIENCIA / TEMA
# =========================

@login_required
@role_required('superadmin', 'director')
def tema_centro(request):
    from .models import TemaCentro, TEMAS_PREDEFINIDOS
    from .forms import TemaCentroForm

    centro_id = request.session.get('centro_id')
    if not centro_id:
        return redirect('core:seleccionar_centro')

    centro = get_object_or_404(CentroEducativo, id=centro_id)
    tema, created = TemaCentro.objects.get_or_create(
        centro=centro,
        defaults=TEMAS_PREDEFINIDOS[0],
    )

    if request.method == 'POST':
        if 'aplicar_tema' in request.POST:
            tema_nombre = request.POST.get('tema_nombre', '')
            for t in TEMAS_PREDEFINIDOS:
                if t['nombre'] == tema_nombre:
                    for campo, valor in t.items():
                        setattr(tema, campo, valor)
                    tema.save()
                    messages.success(request, f'Tema "{tema_nombre}" aplicado.')
                    return redirect('core:tema_centro')

        form = TemaCentroForm(request.POST, instance=tema)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tema actualizado.')
            return redirect('core:tema_centro')
    else:
        form = TemaCentroForm(instance=tema)

    return render(request, 'core/tema_centro.html', {
        'form': form,
        'tema': tema,
        'temas_predefinidos': TEMAS_PREDEFINIDOS,
        'centro': centro,
    })


@login_required
@role_required('superadmin', 'director')
def tema_centro_preview(request):
    """Endpoint AJAX para previsualizar un color en vivo."""
    from django.http import JsonResponse
    from .models import TemaCentro

    centro_id = request.session.get('centro_id')
    if not centro_id:
        return JsonResponse({'error': 'Sin centro'}, status=400)

    tema, _ = TemaCentro.objects.get_or_create(centro_id=centro_id)
    return JsonResponse({
        'css': tema.to_css_variables(),
    })


# =========================
# LOGO DEL CENTRO
# =========================

@login_required
@role_required('superadmin', 'director')
def logo_centro(request):
    centro_id = request.session.get('centro_id')
    if not centro_id:
        return redirect('core:seleccionar_centro')

    centro = get_object_or_404(CentroEducativo, id=centro_id)

    if request.method == 'POST':
        if 'eliminar_logo' in request.POST:
            if centro.logo:
                centro.logo.delete()
                centro.logo = None
                centro.save()
                messages.success(request, 'Logo eliminado.')
            return redirect('core:logo_centro')

        logo = request.FILES.get('logo')
        if logo:
            centro.logo = logo
            centro.save()
            messages.success(request, 'Logo actualizado correctamente.')
            return redirect('core:logo_centro')
        else:
            messages.error(request, 'Selecciona un archivo de imagen.')

    return render(request, 'core/logo_centro.html', {
        'centro': centro,
    })


@login_required
@role_required('director', 'superadmin')
def test_correo(request):

    centro_id = request.session.get('centro_id')

    if not centro_id:
        return redirect('core:seleccionar_centro')

    centro = get_object_or_404(
        CentroEducativo,
        id=centro_id
    )

    if request.method != 'POST':
        return redirect('core:configuracion_centro')

    if not request.user.email:
        messages.error(
            request,
            'Tu usuario no tiene correo configurado. Agrega un email a tu '
            'perfil para recibir el correo de prueba.'
        )
        return redirect('core:configuracion_centro')

    from comunicaciones.services.email import enviar_correo_prueba

    try:
        enviar_correo_prueba(centro, request.user.email)
        messages.success(
            request,
            f'Correo de prueba enviado a {request.user.email}. '
            'Revísalo para confirmar la configuración.'
        )
    except Exception as exc:  # noqa: BLE001 - mostrar el error al usuario
        logger.error('Correo de prueba falló para %s: %s', centro.id, exc)
        messages.error(
            request,
            f'No se pudo enviar el correo de prueba: {exc}'
        )

    return redirect('core:configuracion_centro')

# =========================
# MINI TARJETA DE PERSONA (popover estilo Odoo al pasar el mouse)
# =========================

@login_required
def persona_card_ajax(request):
    """Devuelve los datos de la mini tarjeta de un estudiante, docente o usuario.

    GET /ajax/persona-card/?tipo=estudiante|docente|usuario&id=<pk>
    Solo expone campos seguros (nombre, iniciales, foto, URL de perfil).
    """
    from django.http import JsonResponse
    from django.urls import reverse
    from django.core.exceptions import ObjectDoesNotExist, ValidationError

    tipo = request.GET.get('tipo', '')
    try:
        objeto_id = int(request.GET.get('id', ''))
    except ValueError:
        return JsonResponse({'error': 'id invalido'}, status=400)

    datos = {'nombre': '', 'subtitulo': '', 'iniciales': '?', 'foto_url': None,
             'color': 'from-blue-500 to-indigo-600', 'perfil_url': None}

    try:
        if tipo == 'estudiante':
            from estudiantes.models import Estudiante
            persona = Estudiante.objects.only(
                'primer_nombre', 'segundo_nombre', 'primer_apellido',
                'segundo_apellido', 'matricula', 'foto').get(pk=objeto_id)
            datos.update(
                nombre=persona.nombre_completo(),
                subtitulo=f'Matricula {persona.matricula}',
                iniciales=(persona.primer_nombre[:1] + persona.primer_apellido[:1]).upper(),
                perfil_url=reverse('estudiante_detail', args=[persona.id]),
            )
            if persona.foto:
                datos['foto_url'] = persona.foto.url

        elif tipo == 'docente':
            from docentes.models import Docente
            persona = Docente.objects.select_related(None).only(
                'primer_nombre', 'segundo_nombre', 'primer_apellido',
                'segundo_apellido', 'codigo_docente_minerd', 'foto').get(pk=objeto_id)
            datos.update(
                nombre=persona.nombre_completo(),
                subtitulo=persona.codigo_docente_minerd or 'Docente',
                iniciales=(persona.primer_nombre[:1] + persona.primer_apellido[:1]).upper(),
                perfil_url=reverse('docente_detail', args=[persona.id]),
            )
            if persona.foto:
                datos['foto_url'] = persona.foto.url

        elif tipo == 'usuario':
            from usuarios.models import Usuario
            persona = Usuario.objects.only(
                'first_name', 'last_name', 'username', 'rol', 'foto').get(pk=objeto_id)
            datos.update(
                nombre=persona.get_full_name() or persona.username,
                subtitulo=f'@{persona.username} � {persona.get_rol_display()}',
                iniciales=((persona.first_name[:1] or '') + (persona.last_name[:1] or '')).upper() or '?',
                color='from-indigo-500 to-purple-600',
                # No hay pagina de detalle de terceros: solo el propio perfil.
                perfil_url=(
                    reverse('usuarios:mi_perfil')
                    if persona.id == request.user.id else None
                ),
            )
            if persona.foto:
                datos['foto_url'] = persona.foto.url
        else:
            return JsonResponse({'error': 'tipo invalido'}, status=400)

    except ObjectDoesNotExist:
        return JsonResponse({'error': 'no encontrado'}, status=404)
    except ValidationError:
        return JsonResponse({'error': 'id invalido'}, status=400)

    return JsonResponse(datos)
