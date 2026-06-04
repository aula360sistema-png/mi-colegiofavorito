from ..models import Administrativo, CentroEducativo


def resolver_centro_para_usuario(request):
    """
    Asegura que el centro_id esté en sesión.
    Si no existe, lo obtiene según el rol del usuario.
    Retorna el CentroEducativo o None.
    """
    centro_id = request.session.get('centro_id')

    if centro_id:
        try:
            return CentroEducativo.objects.get(id=centro_id)
        except CentroEducativo.DoesNotExist:
            request.session.pop('centro_id')

    user = request.user

    # Director o Secretaria → Administrativo
    if user.rol in ['director', 'secretaria']:
        admin = Administrativo.objects.filter(usuario=user).select_related('centro').first()
        if admin:
            request.session['centro_id'] = admin.centro.id
            return admin.centro

    return None


