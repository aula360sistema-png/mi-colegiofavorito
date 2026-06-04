from django.shortcuts import redirect

def rol_requerido(rol):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.rol == rol:
                return view_func(request, *args, **kwargs)
            return redirect('login')
        return wrapper
    return decorator
