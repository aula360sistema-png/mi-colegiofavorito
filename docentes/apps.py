from django.apps import AppConfig


class DocentesConfig(AppConfig):
    name = 'docentes'

    def ready(self):
        from . import signals

        signals.conectar_signals()
