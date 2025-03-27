"""
Utilitários para gerenciamento de usuários
"""
from django.db import transaction
from .models import CategoriaCusto, SubcategoriaCusto, User

def replicar_categorias_globais_para_usuario(usuario):
    """
    Replica todas as categorias e subcategorias globais para um usuário específico.
    
    Args:
        usuario: Objeto User para o qual as categorias serão replicadas
    
    Returns:
        tuple: (num_categorias_criadas, num_subcategorias_criadas)
    """
    with transaction.atomic():
        # Busca todas as categorias globais
        categorias_globais = CategoriaCusto.objects.filter(usuario__isnull=True)
        
        # Mapeia IDs de categorias globais para IDs de categorias do usuário
        mapeamento_categorias = {}
        num_categorias_criadas = 0
        
        # Replica cada categoria global
        for cat_global in categorias_globais:
            # Verifica se já existe uma categoria com o mesmo nome para o usuário
            cat_existente = CategoriaCusto.objects.filter(
                nome=cat_global.nome,
                usuario=usuario
            ).first()
            
            if not cat_existente:
                # Cria uma nova categoria para o usuário
                nova_cat = CategoriaCusto.objects.create(
                    nome=cat_global.nome,
                    tipo=cat_global.tipo,
                    alocacao=cat_global.alocacao,
                    usuario=usuario
                )
                mapeamento_categorias[cat_global.id] = nova_cat.id
                num_categorias_criadas += 1
            else:
                # Usa a categoria existente
                mapeamento_categorias[cat_global.id] = cat_existente.id
        
        # Busca todas as subcategorias globais
        subcategorias_globais = SubcategoriaCusto.objects.filter(usuario__isnull=True)
        
        # Replica cada subcategoria global
        num_subcategorias_criadas = 0
        for subcat_global in subcategorias_globais:
            # Verifica se a categoria pai foi replicada
            if subcat_global.categoria_id not in mapeamento_categorias:
                continue
                
            # Obtém o ID da categoria replicada
            categoria_id = mapeamento_categorias[subcat_global.categoria_id]
            
            # Verifica se já existe uma subcategoria com o mesmo nome para o usuário
            subcat_existente = SubcategoriaCusto.objects.filter(
                nome=subcat_global.nome,
                categoria_id=categoria_id,
                usuario=usuario
            ).first()
            
            if not subcat_existente:
                # Cria uma nova subcategoria para o usuário
                SubcategoriaCusto.objects.create(
                    nome=subcat_global.nome,
                    categoria_id=categoria_id,
                    usuario=usuario
                )
                num_subcategorias_criadas += 1
    
    return (num_categorias_criadas, num_subcategorias_criadas)
