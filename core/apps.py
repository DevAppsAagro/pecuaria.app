from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Importa os sinais quando o aplicativo é inicializado
        """
        import core.signals  # noqa
