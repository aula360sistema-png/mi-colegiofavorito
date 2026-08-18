from django.apps import AppConfig


class EstudiantesConfig(AppConfig):
    name = 'estudiantes'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
