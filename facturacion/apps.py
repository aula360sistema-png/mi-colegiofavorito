from django.apps import AppConfig


class FacturacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facturacion'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
