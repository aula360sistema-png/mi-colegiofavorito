from django.db.models.signals import post_save, post_delete

from .models import Docente


def _centro_id_de(instance):
    centro_id = getattr(instance, 'centro_id', None)
    if centro_id is not None:
        return centro_id

    # DocenteMateria: vía el docente.
    docente = getattr(instance, 'docente', None)
    if docente is not None:
        try:
            return docente.centro_id
        except Exception:
            return None

    # PeriodoAnio: vía el período.
    periodo = getattr(instance, 'periodo', None)
    if periodo is not None:
        try:
            return periodo.centro_id
        except Exception:
            return None

    return None


def _invalidar(sender, instance, **kwargs):
    from .services import invalidar_docentes_centro

    centro_id = _centro_id_de(instance)
    if centro_id:
        invalidar_docentes_centro(centro_id)


def conectar_signals():
    from administracion.models import Acta
    from academico.models import DocenteMateria, PeriodoAnio
    from estudiantes.models import Inscripcion

    for modelo in (
        Docente,
        DocenteMateria,
        Acta,
        Inscripcion,
        PeriodoAnio,
    ):
        post_save.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'docentes.{modelo.__name__}.save',
        )
        post_delete.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'docentes.{modelo.__name__}.delete',
        )
