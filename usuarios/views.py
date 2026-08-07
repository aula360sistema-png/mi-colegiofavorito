from django.contrib.auth import authenticate, login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render





from django.contrib.auth import authenticate, login, logout


from administracion.views import administrativo_create
from core.models import CentroEducativo

from django.shortcuts import render, redirect
from docentes.models import Docente
from estudiantes.models import Estudiante

from django_ratelimit.decorators import ratelimit



from django.contrib.auth.decorators import login_required

from docentes.views import docente_create
from estudiantes.views import estudiante_create
from core.utils.session import get_centro_activo

    
@login_required
def crear_miembro(request):
    if request.user.rol not in ['director', 'superadmin']:
        return HttpResponseForbidden()
    
    tipo = request.GET.get('tipo') or request.POST.get('tipo')  # docente | estudiante | secretaria
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    if tipo == "docente":
        return docente_create(request)  # reutiliza la función existente
    elif tipo == "estudiante":
        return estudiante_create(request)  # reutiliza la función existente
    elif tipo == "administrativo":
            return administrativo_create(request)  # nueva función
    else:
        # Si no hay tipo definido, mostramos selector
        return render(request, "usuarios/seleccionar_tipo.html")






# Vistas de autenticación
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', block=True)
def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            centro_id = None

            if user.rol == 'docente' and hasattr(user, 'docente'):
                centro_id = user.docente.centro_id

            elif user.rol in ['director', 'administrativo', 'cajero'] and hasattr(user, 'administrativo'):
                centro_id = user.administrativo.centro_id

            elif user.rol == 'estudiante' and hasattr(user, 'estudiante'):
                centro_id = user.estudiante.centro_id

            if centro_id:
                request.session['centro_id'] = centro_id

            return redirect('core:home')

        return render(request, 'usuarios/login.html', {
            'error': 'Usuario o contraseña incorrectos'
        })

    return render(request, 'usuarios/login.html')
    
@login_required
def logout_view(request):
    logout(request)
    return redirect('usuarios:login')