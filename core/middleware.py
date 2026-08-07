from django.shortcuts import redirect


class CentroMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.excluded_paths = (
            '/',  # home exact
            '/usuarios/login/',
            '/usuarios/logout/',
            '/dashboard-docente/',
            '/dashboard-admin/',
            '/estudiante/',
            '/seleccionar-centro/',
            '/admin/',
        )
        self.roles_sin_selector = ['docente', 'estudiante' ,'director', 'secretaria', 'cajero']

    def __call__(self, request):
        # ❌ Usar exact match
        if request.path in self.excluded_paths:
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        if user.is_superuser:
            return self.get_response(request)

        if user.rol in self.roles_sin_selector:
            return self.get_response(request)

        if not request.session.get('centro_id'):
            return redirect('core:seleccionar_centro')

        return self.get_response(request)
