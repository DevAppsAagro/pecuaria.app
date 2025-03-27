"""
Utilitários para trabalhar com categorias de custo
"""

def is_categoria_estoque(categoria):
    """
    Verifica se uma categoria é do tipo estoque, considerando tanto
    o atributo alocação quanto o nome da categoria (para categorias globais).
    
    Args:
        categoria: Objeto CategoriaCusto
        
    Returns:
        bool: True se a categoria for do tipo estoque, False caso contrário
    """
    # Verifica pelo atributo alocação
    if categoria.alocacao and categoria.alocacao.lower() == 'estoque':
        return True
        
    # Para categorias globais, verifica pelo nome
    if categoria.usuario is None:
        categoria_nome = categoria.nome.lower()
        keywords = ['estoque', 'insumo', 'ração', 'medicamento', 'vacina', 'suplemento']
        return any(keyword.lower() in categoria_nome for keyword in keywords)
        
    return False
