import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from administracion.views import administrativo_create
from core.utils.session import get_centro_activo
from docentes.views import docente_create
from estudiantes.views import estudiante_create
from usuarios.models import Usuario

logger = logging.getLogger('security')

MAX_INTENTOS_LOGIN = 5
VENTANA_INTENTOS = timedelta(minutes=15)
HONEYPOT_FIELD = 'website'


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log(request, usuario, accion, modulo, descripcion, riesgo='BAJO'):
    """Registra el evento en la Bitácora y en el log de seguridad."""
    ip = _get_client_ip(request)
    nombre = usuario.username if usuario else '-'
    logger.info(
        '[%s] %s | %s | usuario=%s | ip=%s | %s',
        riesgo, accion, modulo, nombre, ip, descripcion,
    )
    try:
        from auditoria.models import Bitacora

        centro_id = request.session.get('centro_id')
        centro = None
        if centro_id:
            from core.models import CentroEducativo
            centro = CentroEducativo.objects.filter(id=centro_id).first()

        Bitacora.objects.create(
            usuario=usuario,
            centro=centro,
            accion=accion,
            modulo=modulo,
            descripcion=descripcion,
            ip=ip or None,
            ruta=request.get_full_path(),
            metodo=request.method,
            navegador=(request.META.get('HTTP_USER_AGENT') or '')[:200],
            riesgo=riesgo,
        )
    except Exception:
        pass


def _asignar_centro_sesion(request, user):
    centro_id = None
    if user.rol == 'docente' and hasattr(user, 'docente'):
        centro_id = user.docente.centro_id
    elif user.rol in ['director', 'secretaria', 'cajero'] and hasattr(user, 'administrativo'):
        centro_id = user.administrativo.centro_id
    elif user.rol == 'estudiante' and hasattr(user, 'estudiante'):
        centro_id = user.estudiante.centro_id
    elif user.rol == 'tutor' and hasattr(user, 'tutor'):
        centro_id = user.tutor.centro_id
    if centro_id:
        request.session['centro_id'] = centro_id


@login_required
@ratelimit(key='ip', rate='50/h', method='POST', block=True)
def crear_miembro(request):
    if request.user.rol not in ['director', 'admin', 'superadmin']:
        return HttpResponseForbidden()

    tipo = request.GET.get('tipo') or request.POST.get('tipo')  # docente | estudiante | secretaria
    centro = get_centro_activo(request)
    if not centro:
        return redirect('core:seleccionar_centro')

    if tipo == "docente":
        return docente_create(request)
    elif tipo == "estudiante":
        return estudiante_create(request)
    elif tipo == "administrativo":
        return administrativo_create(request)
    elif tipo == "tutor":
        from tutores.views import tutor_create
        return tutor_create(request)
    else:
        return render(request, "usuarios/seleccionar_tipo.html")


@ratelimit(key='ip', rate='30/5m', block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        llave_usuario = username.lower()

        # Honeypot: campo oculto que un humano deja vacío.
        if request.POST.get(HONEYPOT_FIELD):
            _log(
                request, None, 'ACCESO_DENEGADO', 'Login',
                'Bot detectado por honeypot', 'CRITICO',
            )
            error = 'Usuario o contraseña incorrectos.'
        else:
            llave_bloqueo = f"login_bloqueado:{llave_usuario}"

            if cache.get(llave_bloqueo):
                _log(
                    request, None, 'ACCESO_DENEGADO', 'Login',
                    f"Intento de inicio de sesión en cuenta bloqueada '{username}'", 'CRITICO',
                )
                error = ('Demasiados intentos fallidos. La cuenta está bloqueada '
                         'temporalmente, inténtalo en unos minutos.')
            else:
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    cache.delete(f"login_fallidos:{llave_usuario}")
                    request.session['_2fa_pendiente'] = user.pk

                    if user.requiere_2fa():
                        if not user.totp_activo:
                            return redirect('usuarios:configurar_2fa')
                        return redirect('usuarios:verificar_2fa')

                    login(request, user)
                    request.session.pop('_2fa_pendiente', None)
                    _asignar_centro_sesion(request, user)
                    _log(request, user, 'LOGIN', 'Login', 'Inicio de sesión exitoso', 'BAJO')
                    return redirect('core:home')

                fallos = cache.get(f"login_fallidos:{llave_usuario}", 0) + 1
                cache.set(
                    f"login_fallidos:{llave_usuario}",
                    fallos,
                    int(VENTANA_INTENTOS.total_seconds()),
                )
                _log(
                    request, None, 'LOGIN_FAILED', 'Login',
                    f"Intento de inicio de sesión fallido para '{username}'", 'ALTO',
                )

                if fallos >= MAX_INTENTOS_LOGIN:
                    cache.delete(f"login_fallidos:{llave_usuario}")
                    cache.set(llave_bloqueo, True, int(VENTANA_INTENTOS.total_seconds()))
                    _log(
                        request, None, 'ACCESO_DENEGADO', 'Login',
                        f"Cuenta '{username}' bloqueada temporalmente por {MAX_INTENTOS_LOGIN} "
                        "intentos fallidos", 'CRITICO',
                    )
                    error = ('Demasiados intentos fallidos. La cuenta está bloqueada '
                             'temporalmente, inténtalo en unos minutos.')
                else:
                    error = 'Usuario o contraseña incorrectos.'

    return render(request, 'usuarios/login.html', {'error': error})


@ratelimit(key='ip', rate='10/5m', block=True)
def verificar_2fa(request):
    user_id = request.session.get('_2fa_pendiente')
    if not user_id:
        return redirect('usuarios:login')
    user = get_object_or_404(Usuario, pk=user_id)

    error = None
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().replace(' ', '')
        if user.verificar_totp(codigo):
            request.session.pop('_2fa_pendiente', None)
            login(request, user)
            _asignar_centro_sesion(request, user)
            _log(request, user, 'LOGIN', 'Login', 'Inicio de sesión exitoso (2FA verificado)', 'BAJO')
            return redirect('core:home')
        error = 'El código no es válido o ha expirado.'
        _log(
            request, None, 'LOGIN_FAILED', 'Login',
            f"Código 2FA incorrecto para '{user.username}'", 'ALTO',
        )

    return render(request, 'usuarios/verificar_2fa.html', {'error': error, 'usuario': user})


@ratelimit(key='ip', rate='10/5m', block=True)
def configurar_2fa(request):
    user_id = request.session.get('_2fa_pendiente')
    if not user_id:
        return redirect('usuarios:login')
    user = get_object_or_404(Usuario, pk=user_id)
    user.generar_totp()

    error = None
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().replace(' ', '')
        if user.verificar_totp(codigo):
            user.totp_activo = True
            user.save(update_fields=['totp_activo'])
            request.session.pop('_2fa_pendiente', None)
            login(request, user)
            _asignar_centro_sesion(request, user)
            _log(request, user, 'ACTIVAR_2FA', 'Usuarios', '2FA configurado y activado', 'MEDIO')
            _log(request, user, 'LOGIN', 'Login', 'Inicio de sesión exitoso (2FA configurado)', 'BAJO')
            return redirect('core:home')
        error = 'El código no es válido. Verifica que la app esté sincronizada.'

    return render(request, 'usuarios/configurar_2fa.html', {
        'error': error,
        'usuario': user,
        'uri': user.uri_totp(),
        'secret': user.totp_secret,
    })


@login_required
def gestionar_2fa(request):
    user = request.user
    error = None
    info = None

    if request.method == 'POST':
        accion = request.POST.get('accion')
        codigo = request.POST.get('codigo', '').strip().replace(' ', '')
        if not user.verificar_totp(codigo):
            error = 'El código no es válido o ha expirado.'
        elif accion == 'activar':
            user.totp_activo = True
            user.save(update_fields=['totp_activo'])
            _log(request, user, 'ACTIVAR_2FA', 'Usuarios', '2FA activado', 'MEDIO')
            info = 'Autenticación de dos factores activada.'
        elif accion == 'desactivar':
            if user.tiene_2fa_obligatorio():
                error = 'Tu rol no permite desactivar la autenticación de dos factores.'
            else:
                user.totp_activo = False
                user.save(update_fields=['totp_activo'])
                _log(request, user, 'DESACTIVAR_2FA', 'Usuarios', '2FA desactivado', 'MEDIO')
                info = 'Autenticación de dos factores desactivada.'

    if not user.totp_secret:
        user.generar_totp()

    return render(request, 'usuarios/gestionar_2fa.html', {
        'error': error,
        'info': info,
        'uri': user.uri_totp(),
        'secret': user.totp_secret,
    })


@login_required
def logout_view(request):
    _log(request, request.user, 'LOGOUT', 'Login', 'Cierre de sesión', 'BAJO')
    logout(request)
    return redirect('usuarios:login')


@login_required
def mi_perfil(request):
    user = request.user

    perfil = None
    if user.rol == 'docente':
        perfil = getattr(user, 'docente', None)
    elif user.rol == 'estudiante':
        perfil = getattr(user, 'estudiante', None)
    elif user.rol == 'tutor':
        perfil = getattr(user, 'tutor', None)
    else:
        perfil = getattr(user, 'administrativo', None)

    ctx = {
        'centro': get_centro_activo(request),
        'perfil': perfil,
        'dias_password': None,
        'requiere_2fa': user.requiere_2fa(),
    }
    if user.password_cambiada_en:
        ctx['dias_password'] = (timezone.now() - user.password_cambiada_en).days

    return render(request, 'usuarios/mi_perfil.html', ctx)


@login_required
def cambiar_contrasena(request):
    errores = []

    if request.method == 'POST':
        actual = request.POST.get('password_actual', '')
        nueva = request.POST.get('password_nueva', '')
        confirmacion = request.POST.get('password_confirmacion', '')

        if not request.user.check_password(actual):
            errores.append('La contraseña actual no es correcta.')
        elif nueva != confirmacion:
            errores.append('La nueva contraseña no coincide con la confirmación.')
        else:
            try:
                validate_password(nueva, user=request.user)
            except ValidationError as exc:
                errores.extend(exc.messages)
            else:
                request.user.set_password(nueva)
                request.user.debe_cambiar_password = False
                request.user.password_cambiada_en = timezone.now()
                request.user.save(update_fields=[
                    'password', 'debe_cambiar_password', 'password_cambiada_en',
                ])
                update_session_auth_hash(request, request.user)
                _log(
                    request, request.user, 'PASSWORD_CHANGE', 'Usuarios',
                    'Cambio de contraseña', 'MEDIO',
                )
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('core:home')

    return render(request, 'usuarios/cambiar_contrasena.html', {'errores': errores})
