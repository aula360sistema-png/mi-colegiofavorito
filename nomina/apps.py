from django.apps import AppConfig


class NominaConfig(AppConfig):
    name = 'nomina'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
