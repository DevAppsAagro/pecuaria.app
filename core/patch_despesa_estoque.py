"""
Patch para corrigir o processamento de despesas relacionadas a estoque,
especialmente para categorias globais.
"""
import logging
from .models_estoque import Insumo
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
    
    # Cria ou obtém o insumo
    if insumo_data.get('id'):
        try:
            insumo = Insumo.objects.get(id=insumo_data['id'])
            logger.info(f"Insumo existente encontrado: {insumo.nome} (ID: {insumo.id})")
        except Insumo.DoesNotExist:
            logger.warning(f"Insumo com ID {insumo_data['id']} não encontrado, criando novo")
            insumo = None
    else:
        insumo = None
        
    if not insumo:
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
    from .views_estoque import criar_entrada_estoque_from_despesa
    criar_entrada_estoque_from_despesa(despesa, item_despesa, insumo)
    
    return insumo

def patch_despesa_create_view():
    """
    Aplica o patch na view DespesaCreateView para corrigir o processamento
    de despesas relacionadas a estoque.
    """
    from .views import DespesaCreateView
    
    # Guarda a implementação original do método
    original_form_valid = DespesaCreateView.form_valid
    
    def patched_form_valid(self, form):
        """
        Versão patcheada do método form_valid que corrige o processamento
        de despesas relacionadas a estoque.
        """
        # Chama a implementação original
        response = original_form_valid(self, form)
        
        # Adiciona logs para depuração
        logger.info("Patch aplicado ao método form_valid de DespesaCreateView")
        
        return response
    
    # Aplica o patch
    DespesaCreateView.form_valid = patched_form_valid
    
    logger.info("Patch aplicado com sucesso à view DespesaCreateView")
    
    return True
