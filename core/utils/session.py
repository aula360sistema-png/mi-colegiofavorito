from core.models import CentroEducativo


def get_centro_activo(request):
    centro_id = request.session.get('centro_id')

    if not centro_id:
        return None

    try:
        return CentroEducativo.objects.get(id=centro_id)

    except CentroEducativo.DoesNotExist:
        return None
    