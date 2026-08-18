from django.apps import AppConfig


class AsistenciaConfig(AppConfig):
    name = 'asistencia'

    def ready(self):
        from . import signals

        signals.conectar_signals()
