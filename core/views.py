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
        return redirect('caja:caja_inicio')

    # 🏫 DIRECTOR / SECRETARIA → ya tienen centro
    if user.rol in ['director', 'secretaria']:
        return redirect('administracion:dashboard_admin')

    # 🔥 SUPERADMIN → debe elegir centro
    if user.rol == 'superadmin':
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

            return redirect('core:configuracion_centro')

    else:

        form = ConfiguracionCentroForm(
            instance=configuracion
        )

    return render(
        request,
        'core/configuracion_centro.html',
        {
            'form': form,
            'centro': centro
        }
    )


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