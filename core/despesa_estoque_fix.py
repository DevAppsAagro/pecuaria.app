"""
Correção para o processamento de despesas relacionadas a estoque,
especialmente para categorias globais.

Este módulo deve ser importado no arquivo __init__.py do aplicativo
para aplicar automaticamente as correções necessárias.
"""
import logging
from decimal import Decimal
from django.db import transaction
from .models_estoque import Insumo, MovimentacaoEstoque
from .categoria_utils import is_categoria_estoque

logger = logging.getLogger(__name__)

def criar_entrada_estoque_corrigida(despesa, item_despesa, insumo):
    """
    Versão corrigida da função criar_entrada_estoque_from_despesa que lida corretamente
    com categorias globais, mesmo quando não há fazenda de destino definida.
    
    Args:
        despesa: Objeto Despesa
        item_despesa: Objeto ItemDespesa
        insumo: Objeto Insumo
        
    Returns:
        MovimentacaoEstoque: A movimentação de estoque criada ou None em caso de erro
    """
    logger.info(f"Criando entrada de estoque corrigida para despesa {despesa.id}, item {item_despesa.id}, insumo {insumo.nome}")
    
    # Verifica se a categoria é do tipo estoque
    if not is_categoria_estoque(item_despesa.categoria):
        logger.warning(f"Categoria {item_despesa.categoria.nome} não é do tipo estoque. Alocação: {item_despesa.categoria.alocacao}")
        return None
    
    # Log detalhado para depuração
    logger.info(f"Categoria: {item_despesa.categoria.nome} (ID: {item_despesa.categoria.id}, Alocação: {item_despesa.categoria.alocacao})")
    logger.info(f"Usuário da categoria: {item_despesa.categoria.usuario_id if item_despesa.categoria.usuario_id else 'Global'}")
    
    # Verifica se há uma fazenda de destino
    if not item_despesa.fazenda_destino:
        logger.warning(f"Item de despesa {item_despesa.id} não tem fazenda de destino definida")
        # Continua mesmo sem fazenda de destino para categorias globais
        if not item_despesa.categoria.usuario_id:  # Se for categoria global
            logger.info("Categoria global detectada, continuando mesmo sem fazenda de destino")
        else:
            # Para categorias do usuário, ainda exigimos a fazenda de destino
            logger.error("Categoria do usuário requer fazenda de destino, abortando criação de entrada de estoque")
            return None
    else:
        logger.info(f"Fazenda de destino: {item_despesa.fazenda_destino.nome} (ID: {item_despesa.fazenda_destino.id})")
    
    try:
        with transaction.atomic():
            # Cria a movimentação de estoque
            movimentacao = MovimentacaoEstoque.objects.create(
                insumo=insumo,
                tipo='E',
                data=despesa.data_emissao,
                quantidade=item_despesa.quantidade,
                valor_unitario=item_despesa.valor_unitario,
                valor_total=item_despesa.valor_total,
                despesa=despesa,
                usuario=despesa.usuario
            )
            
            # Atualiza o saldo e preço médio do insumo
            quantidade_anterior = insumo.saldo_estoque or Decimal('0')
            valor_anterior = quantidade_anterior * (insumo.preco_medio or Decimal('0'))
            
            # Calcula o novo saldo e preço médio
            nova_quantidade = quantidade_anterior + item_despesa.quantidade
            novo_valor_total = valor_anterior + item_despesa.valor_total
            
            if nova_quantidade > 0:
                novo_preco_medio = novo_valor_total / nova_quantidade
            else:
                novo_preco_medio = Decimal('0')
            
            # Atualiza o insumo
            insumo.saldo_estoque = nova_quantidade
            insumo.preco_medio = novo_preco_medio
            insumo.valor_total = novo_valor_total
            insumo.save()
            
            logger.info(f"Entrada de estoque criada: ID {movimentacao.id} para insumo {insumo.nome}")
            logger.info(f"Insumo atualizado: saldo={insumo.saldo_estoque}, preço médio={insumo.preco_medio}, valor total={insumo.valor_total}")
            
            return movimentacao
    except Exception as e:
        logger.error(f"Erro ao criar entrada de estoque: {str(e)}")
        return None

# Monkey patch para substituir a função original
def aplicar_patch():
    """
    Aplica o patch para substituir a função original criar_entrada_estoque_from_despesa
    pela versão corrigida.
    """
    from .views_estoque import criar_entrada_estoque_from_despesa
    import types
    
    # Guarda uma referência à função original para debug
    original_function = criar_entrada_estoque_from_despesa
    
    # Substitui a função original pela versão corrigida
    criar_entrada_estoque_from_despesa.__code__ = criar_entrada_estoque_corrigida.__code__
    
    logger.info("Patch aplicado: função criar_entrada_estoque_from_despesa substituída pela versão corrigida")
    
    return True
