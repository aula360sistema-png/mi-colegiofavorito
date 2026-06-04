from django.apps import AppConfig


class AuditoriaConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'

    name = 'auditoria'

    verbose_name = 'Auditoría Inteligente'

    def ready(self):

        from .signals import conectar_signals

        conectar_signals()