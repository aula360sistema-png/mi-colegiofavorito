

from core.models import CentroEducativo


def obtener_centro_del_usuario(request):
    user = request.user

    # SUPERADMIN → desde sesión
    if user.rol == 'superadmin':
        return CentroEducativo.objects.filter(
            id=request.session.get('centro_id')
        ).first()

    # ADMINISTRATIVO (director / secretaria / cajero)
    if user.rol in ['director', 'secretaria', 'cajero'] and hasattr(user, 'administrativo'):
        return user.administrativo.centro

    # DOCENTE
    if user.rol == 'docente' and hasattr(user, 'docente'):
        return user.docente.centro

    # ESTUDIANTE
    if user.rol == 'estudiante' and hasattr(user, 'estudiante'):
        return user.estudiante.centro

    return None