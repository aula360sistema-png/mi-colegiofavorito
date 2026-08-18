from django.apps import AppConfig


class ComunicacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comunicaciones'
    verbose_name = 'Comunicaciones'

    def ready(self):
        from .signals import conectar_signals
        conectar_signals()
