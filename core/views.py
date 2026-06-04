from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from core.decorators import role_required
from .models import CentroEducativo, ConfiguracionCentro, UsuarioCentro

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


@role_required('superadmin')
def custom_404_view(request, exception):
    if request.user.is_authenticated:
        return redirect('home')  # o dashboard
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
        return redirect('seleccionar_centro')

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

    centros = CentroEducativo.objects.all().order_by('nombre')

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
            form.save()
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