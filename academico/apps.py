from django.apps import AppConfig


class AcademicoConfig(AppConfig):
    name = 'academico'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
