from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Importa os sinais quando o aplicativo é inicializado e aplica os patches necessários
        """
        import core.signals  # noqa
        
        # Aplicar os patches quando o aplicativo estiver pronto
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Importar a função aplicar_patches do módulo core
            from core import aplicar_patches
            # Aplicar os patches
            aplicar_patches()
            logger.info("Patches aplicados com sucesso durante a inicialização do aplicativo")
        except Exception as e:
            logger.error(f"Erro ao aplicar patches durante a inicialização do aplicativo: {e}")
