from django.apps import AppConfig


class CajaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'caja'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
