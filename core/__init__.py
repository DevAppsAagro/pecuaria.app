"""
Aplicativo core do sistema Pecuária.app
"""

# Aplica o patch para correção do processamento de despesas relacionadas a estoque
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

# Aplica os patches ao importar o módulo
aplicar_patches()
