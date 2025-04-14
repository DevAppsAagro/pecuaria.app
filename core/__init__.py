"""
Aplicativo core do sistema Pecuária.app
"""

# Define o app_config padrão
default_app_config = 'core.apps.CoreConfig'

# Configuração para aplicar patches automaticamente
def aplicar_patches():
    """
    Aplica os patches necessários para correção de bugs e melhorias no sistema.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Patch para correção do processamento de despesas relacionadas a estoque
        from .despesa_estoque_fix import aplicar_patch
        aplicar_patch()
        logger.info("Patch para correção de despesas de estoque aplicado com sucesso")
        
        # Patch para o método form_valid da classe DespesaCreateView
        from .despesa_form_patch import patch_form_valid
        from . import views
        patch_form_valid(views)
        logger.info("Patch para o método form_valid da classe DespesaCreateView aplicado com sucesso")
        
        # Patch específico para o problema de destino não sendo salvo corretamente
        from .despesa_destino_fix import aplicar_patch_destino
        aplicar_patch_destino()
        logger.info("Patch para correção de destinos aplicado com sucesso")
        
        # Patch direto para o problema de destino não sendo salvo corretamente
        from .destino_fix import corrigir_form_valid
        corrigir_form_valid()
        logger.info("Patch direto para correção de destinos no método form_valid aplicado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao aplicar patches: {str(e)}")

# Não aplicar os patches automaticamente na importação do módulo
# Em vez disso, vamos usar o sistema de sinais do Django para aplicá-los quando o app estiver pronto

# Registrar uma função para ser chamada quando o Django estiver pronto
def ready_handler(sender, **kwargs):
    # Importar aqui para evitar importações circulares
    from django.apps import apps
    if apps.is_installed('core'):
        aplicar_patches()

# Registrar o handler para o sinal 'ready' apenas se estiver em um contexto Django
try:
    from django.apps import AppConfig
    from django.db.models.signals import post_migrate
    
    # Registrar o handler para ser chamado após a migração do banco de dados
    post_migrate.connect(ready_handler, sender=AppConfig)
except ImportError:
    # Se não estiver em um contexto Django, não fazer nada
    pass
