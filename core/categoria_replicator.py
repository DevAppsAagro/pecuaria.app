"""
Utilitário para replicar categorias globais para usuários
"""
from django.db import transaction
from .models import CategoriaCusto, SubcategoriaCusto, User
import csv
import os
from django.conf import settings

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
                print(f"Categoria '{cat_global.nome}' replicada para o usuário {usuario.username}")
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
                print(f"Subcategoria '{subcat_global.nome}' replicada para o usuário {usuario.username}")
    
    return (num_categorias_criadas, num_subcategorias_criadas)

def criar_categorias_from_csv(csv_file_path, usuario=None):
    """
    Cria categorias e subcategorias a partir de um arquivo CSV.
    Se usuario for None, cria categorias globais.
    
    Formato do CSV para categorias:
    nome,tipo,alocacao
    
    Formato do CSV para subcategorias:
    nome,categoria_nome
    
    Args:
        csv_file_path: Caminho para o arquivo CSV
        usuario: Objeto User ou None para categorias globais
        
    Returns:
        int: Número de categorias/subcategorias criadas
    """
    with transaction.atomic():
        count = 0
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Pula o cabeçalho
            
            # Determina o tipo de CSV (categorias ou subcategorias)
            is_categoria = 'tipo' in header and 'alocacao' in header
            
            for row in reader:
                if is_categoria:
                    nome, tipo, alocacao = row
                    # Verifica se a categoria já existe
                    categoria_existente = CategoriaCusto.objects.filter(
                        nome=nome,
                        usuario=usuario
                    ).first()
                    
                    if not categoria_existente:
                        CategoriaCusto.objects.create(
                            nome=nome,
                            tipo=tipo,
                            alocacao=alocacao,
                            usuario=usuario
                        )
                        count += 1
                        print(f"Categoria '{nome}' criada")
                else:
                    nome, categoria_nome = row
                    # Busca a categoria pai
                    categoria = CategoriaCusto.objects.filter(
                        nome=categoria_nome,
                        usuario=usuario
                    ).first()
                    
                    if categoria:
                        # Verifica se a subcategoria já existe
                        subcat_existente = SubcategoriaCusto.objects.filter(
                            nome=nome,
                            categoria=categoria,
                            usuario=usuario
                        ).first()
                        
                        if not subcat_existente:
                            SubcategoriaCusto.objects.create(
                                nome=nome,
                                categoria=categoria,
                                usuario=usuario
                            )
                            count += 1
                            print(f"Subcategoria '{nome}' criada para categoria '{categoria_nome}'")
        
        return count

def replicar_categorias_para_todos_usuarios():
    """
    Replica todas as categorias globais para todos os usuários existentes.
    
    Returns:
        dict: Estatísticas de replicação por usuário
    """
    stats = {}
    for usuario in User.objects.all():
        cat_count, subcat_count = replicar_categorias_globais_para_usuario(usuario)
        stats[usuario.username] = {
            'categorias': cat_count,
            'subcategorias': subcat_count
        }
    
    return stats
