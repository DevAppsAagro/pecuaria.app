import logging
from .models_estoque import Insumo, MovimentacaoEstoque
from .categoria_utils import is_categoria_estoque

logger = logging.getLogger(__name__)

def processar_item_despesa_estoque(despesa, item_despesa, categoria, subcategoria, insumo_data, usuario):
    """
    Processa um item de despesa relacionado a estoque, criando ou atualizando o insumo
    e gerando a movimentação de estoque correspondente.
    
    Args:
        despesa: Objeto Despesa
        item_despesa: Objeto ItemDespesa
        categoria: Objeto CategoriaCusto
        subcategoria: Objeto SubcategoriaCusto
        insumo_data: Dicionário com dados do insumo
        usuario: Objeto User
    
    Returns:
        Objeto Insumo criado ou atualizado
    """
    logger.info(f"Processando item de despesa {item_despesa.id} como estoque")
    logger.info(f"Categoria: {categoria.nome} (ID: {categoria.id}, Alocação: {categoria.alocacao})")
    logger.info(f"Usuário da categoria: {categoria.usuario_id if categoria.usuario_id else 'Global'}")
    logger.info(f"Dados do insumo: {insumo_data}")
    
    # Verifica se é uma categoria de estoque
    if not is_categoria_estoque(categoria):
        logger.warning(f"Categoria {categoria.nome} não é do tipo estoque. Alocação: {categoria.alocacao}")
        return None
    
    # Verifica se há uma fazenda de destino
    if not item_despesa.fazenda_destino:
        logger.warning(f"Item de despesa {item_despesa.id} não tem fazenda de destino definida")
        # Para categorias globais, podemos continuar mesmo sem fazenda de destino
        if not categoria.usuario_id:
            logger.info("Categoria global detectada, continuando mesmo sem fazenda de destino")
        else:
            logger.error("Categoria do usuário requer fazenda de destino, abortando processamento")
            return None
    
    # Cria ou obtém o insumo
    if insumo_data.get('id'):
        insumo = Insumo.objects.get(id=insumo_data['id'])
        logger.info(f"Insumo existente encontrado: {insumo.nome} (ID: {insumo.id})")
    else:
        logger.info(f"Criando novo insumo: {insumo_data['nome']}")
        insumo = Insumo.objects.create(
            nome=insumo_data['nome'],
            categoria=categoria,
            subcategoria=subcategoria,
            unidade_medida_id=insumo_data['unidade_medida_id'],
            usuario=usuario
        )
        logger.info(f"Novo insumo criado: {insumo.nome} (ID: {insumo.id})")
    
    # Cria a movimentação de estoque
    movimentacao = MovimentacaoEstoque.objects.create(
        insumo=insumo,
        tipo='E',
        data=despesa.data_emissao,
        quantidade=item_despesa.quantidade,
        valor_unitario=item_despesa.valor_unitario,
        valor_total=item_despesa.valor_total,
        despesa=despesa,
        usuario=usuario
    )
    
    logger.info(f"Movimentação de estoque criada: ID {movimentacao.id}")
    if item_despesa.fazenda_destino:
        logger.info(f"Fazenda de destino: {item_despesa.fazenda_destino.nome} (ID: {item_despesa.fazenda_destino.id})")
    else:
        logger.info("Sem fazenda de destino definida (categoria global)")
    
    return insumo
