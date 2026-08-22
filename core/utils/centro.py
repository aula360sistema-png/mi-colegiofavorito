

from core.models import CentroEducativo


def obtener_centro_del_usuario(request):
    user = request.user

    # SUPERADMIN / ADMIN → desde sesión
    if user.rol in ('superadmin', 'admin'):
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

    # TUTOR
    if user.rol == 'tutor' and hasattr(user, 'tutor'):
        return user.tutor.centro

    return None