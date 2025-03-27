"""
Utilitários para trabalhar com despesas
"""
from .categoria_utils import is_categoria_estoque
from .models import Insumo
from .views_estoque import criar_entrada_estoque_from_despesa

def processar_item_estoque(despesa, item_despesa, item_data, usuario):
    """
    Processa um item de despesa relacionado a estoque.
    Verifica se a categoria é de estoque usando a função utilitária,
    e cria ou atualiza o insumo conforme necessário.
    
    Args:
        despesa: Objeto Despesa
        item_despesa: Objeto ItemDespesa
        item_data: Dicionário com dados do item
        usuario: Objeto User
        
    Returns:
        bool: True se o item foi processado como estoque, False caso contrário
    """
    # Verifica se a categoria é do tipo estoque usando a função utilitária
    if not is_categoria_estoque(item_despesa.categoria):
        return False
        
    # Verifica se há dados de insumo
    if 'insumo' not in item_data:
        return False
        
    # Processa o insumo
    insumo_data = item_data['insumo']
    if insumo_data['id']:
        insumo = Insumo.objects.get(id=insumo_data['id'])
    else:
        insumo = Insumo.objects.create(
            nome=insumo_data['nome'],
            categoria=item_despesa.categoria,
            subcategoria=item_despesa.subcategoria,
            unidade_medida_id=insumo_data['unidade_medida_id'],
            usuario=usuario
        )
    
    # Cria a movimentação de estoque
    criar_entrada_estoque_from_despesa(despesa, item_despesa, insumo)
    return True
