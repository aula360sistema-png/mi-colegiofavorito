from django.apps import AppConfig


class TutoresConfig(AppConfig):
    name = 'tutores'

    def ready(self):
        from . import signals

        signals.conectar_signals()
