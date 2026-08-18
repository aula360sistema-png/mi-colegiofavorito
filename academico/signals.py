from django.db.models.signals import post_save, post_delete

from .models import (
    AreaCurricular,
    Asignatura,
    Competencia,
    DocenteMateria,
    FranjaHoraria,
    Grado,
    GradoAsignatura,
    HorarioClase,
    Nivel,
    Periodo,
    PeriodoAnio,
    Seccion,
)

# Cada modelo expone cómo obtener el centro que le corresponde. En los
# post_delete las FK relacionadas siguen accesibles a través del objeto.


def _centro_id_de(instance):
    if hasattr(instance, 'centro_id') and instance.centro_id is not None:
        return instance.centro_id

    if isinstance(instance, (Grado, Competencia)):
        return getattr(instance.nivel, 'centro_id', None)

    if isinstance(instance, GradoAsignatura):
        return getattr(instance.grado.nivel, 'centro_id', None)

    if isinstance(instance, PeriodoAnio):
        return getattr(instance.periodo, 'centro_id', None)

    if isinstance(instance, DocenteMateria):
        return getattr(instance.docente, 'centro_id', None)

    if isinstance(instance, HorarioClase):
        return getattr(instance.asignacion.docente, 'centro_id', None)

    return None


def _invalidar(sender, instance, **kwargs):
    from .services.estructura import invalidar_estructura

    centro_id = _centro_id_de(instance)
    if centro_id:
        invalidar_estructura(centro_id)


MODELOS = (
    Nivel,
    Grado,
    Seccion,
    AreaCurricular,
    Asignatura,
    GradoAsignatura,
    Competencia,
    Periodo,
    PeriodoAnio,
    DocenteMateria,
    FranjaHoraria,
    HorarioClase,
)


def conectar_signals():
    for modelo in MODELOS:
        post_save.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'academico.{modelo.__name__}.save',
        )
        post_delete.connect(
            _invalidar,
            sender=modelo,
            dispatch_uid=f'academico.{modelo.__name__}.delete',
        )
