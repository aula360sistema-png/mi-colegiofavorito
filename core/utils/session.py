from core.models import CentroEducativo
from core.utils.centro import obtener_centro_del_usuario


def get_centro_activo(request):
    centro_id = request.session.get('centro_id')

    if not centro_id:
        # Los miembros (director/secretaria/cajero/docente/estudiante) ya
        # pertenecen a un centro: se asigna automáticamente en lugar de pedir
        # que elijan uno.
        if request.user.is_authenticated:
            centro = obtener_centro_del_usuario(request)
            if centro:
                request.session['centro_id'] = centro.id
                return centro
        return None

    try:
        return CentroEducativo.objects.get(id=centro_id)

    except CentroEducativo.DoesNotExist:
        return None
