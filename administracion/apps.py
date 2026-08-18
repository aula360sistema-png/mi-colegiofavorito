from django.apps import AppConfig


class AdministracionConfig(AppConfig):
    name = 'administracion'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
