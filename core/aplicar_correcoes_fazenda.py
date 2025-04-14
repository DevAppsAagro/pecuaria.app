"""
Script para corrigir o problema de filtro por fazenda_id no modelo Despesa.
Este script deve ser executado uma vez para aplicar as correções necessárias.
"""

import logging
import os
import sys
import django

# Configurar o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar o diretório pai ao path para importar o projeto Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pecuaria.settings')
django.setup()

def aplicar_correcoes_fazenda():
    """
    Aplica correções para o problema de filtro por fazenda_id no modelo Despesa.
    """
    logger.info("Iniciando aplicação de correções para o problema de filtro por fazenda_id...")
    
    # Importar os módulos necessários
    from django.apps import apps
    
    # Verificar se o modelo Despesa existe
    if not apps.is_installed('core') or not apps.get_model('core', 'Despesa'):
        logger.error("Modelo Despesa não encontrado!")
        return False
    
    # Caminho para o arquivo views_dashboard_simples.py
    arquivo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views_dashboard_simples.py')
    
    if not os.path.exists(arquivo_path):
        logger.error(f"Arquivo {arquivo_path} não encontrado!")
        return False
    
    # Ler o conteúdo do arquivo
    with open(arquivo_path, 'r', encoding='utf-8') as file:
        conteudo = file.read()
    
    # Correções a serem aplicadas
    
    # 1. Corrigir a função obter_dados_financeiros
    correcao1 = """    try:
        # Definir período para análise
        hoje = date.today()
        if data_inicio is None:
            inicio_mes_atual = date(hoje.year, hoje.month, 1)
            fim_mes_atual = (inicio_mes_atual + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            inicio_mes_atual = data_inicio
            fim_mes_atual = hoje
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        
        # Obter saldo total
        saldo_total = 0
        contas = ContaBancaria.objects.filter(**filtro_usuario)
        
        # Não filtrar por fazenda, já que o modelo não tem esse campo
        
        for conta in contas:
            saldo_total += conta.saldo
        
        # Obter despesas não pagas
        # Verificar se o campo correto é 'situacao' ou 'status'
        try:
            despesas = Despesa.objects.filter(
                status='PENDENTE',  # Usando 'status' em vez de 'situacao'
                **filtro_usuario
            )
            total_despesas_pendentes = despesas.aggregate(total=Sum('itens__valor_total'))['total'] or 0
        except Exception as despesa_error:
            logger.error(f"Erro ao obter despesas: {despesa_error}")
            total_despesas_pendentes = 0
        
        # Obter receitas pendentes
        try:
            # Verificar se o modelo Receita existe
            from django.apps import apps
            if apps.is_installed('core') and apps.get_model('core', 'Receita'):
                Receita = apps.get_model('core', 'Receita')
                receitas = Receita.objects.filter(
                    status='PENDENTE',  # Usando 'status' em vez de 'situacao'
                    **filtro_usuario
                )
                total_receitas_pendentes = receitas.aggregate(total=Sum('valor'))['total'] or 0
            else:
                total_receitas_pendentes = 0
        except Exception as receita_error:
            logger.error(f"Erro ao obter receitas: {receita_error}")
            total_receitas_pendentes = 0"""
    
    padrao1 = """    try:
        # Definir período para análise
        hoje = date.today()
        if data_inicio is None:
            inicio_mes_atual = date(hoje.year, hoje.month, 1)
            fim_mes_atual = (inicio_mes_atual + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            inicio_mes_atual = data_inicio
            fim_mes_atual = hoje
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        
        # Obter saldo total
        saldo_total = 0
        contas = ContaBancaria.objects.filter(**filtro_usuario)
        
        # Não filtrar por fazenda, já que o modelo não tem esse campo
        
        for conta in contas:
            saldo_total += conta.saldo
        
        # Obter despesas não pagas
        despesas = Despesa.objects.filter(
            situacao='PENDENTE',
            **filtro_usuario
        )
        
        # Não filtrar por fazenda, já que o modelo não tem esse campo
        
        total_despesas_pendentes = despesas.aggregate(total=Sum('valor'))['total'] or 0
        
        # Obter receitas pendentes
        receitas = Receita.objects.filter(
            situacao='PENDENTE',
            **filtro_usuario
        )
        
        # Não filtrar por fazenda, já que o modelo não tem esse campo
        
        total_receitas_pendentes = receitas.aggregate(total=Sum('valor'))['total'] or 0"""
    
    # 2. Corrigir a função obter_entradas_saidas_12_meses
    correcao2 = """            # Despesas
            despesas = Despesa.objects.filter(
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                # Usar itens__fazenda_destino_id em vez de fazenda_id
                despesas = despesas.filter(itens__fazenda_destino_id=fazenda_id).distinct()"""
    
    padrao2 = """            # Despesas
            despesas = Despesa.objects.filter(
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                despesas = despesas.filter(**filtro_fazenda)"""
    
    # 3. Corrigir a função obter_categorias_custo
    correcao3 = """        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            # Usar itens__fazenda_destino_id em vez de fazenda_id
            despesas = despesas.filter(itens__fazenda_destino_id=fazenda_id).distinct()"""
    
    padrao3 = """        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            despesas = despesas.filter(**filtro_fazenda)"""
    
    # 4. Corrigir a função obter_contas_a_pagar
    correcao4 = """        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            # Usar itens__fazenda_destino_id em vez de fazenda_id
            despesas = despesas.filter(itens__fazenda_destino_id=fazenda_id).distinct()"""
    
    padrao4 = """        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            despesas = despesas.filter(**filtro_fazenda)"""
    
    # Aplicar as correções
    novo_conteudo = conteudo
    
    # Aplicar correção 1
    if padrao1 in novo_conteudo:
        novo_conteudo = novo_conteudo.replace(padrao1, correcao1)
        logger.info("Correção 1 aplicada com sucesso!")
    else:
        logger.warning("Padrão 1 não encontrado no arquivo!")
    
    # Aplicar correção 2
    if padrao2 in novo_conteudo:
        novo_conteudo = novo_conteudo.replace(padrao2, correcao2)
        logger.info("Correção 2 aplicada com sucesso!")
    else:
        logger.warning("Padrão 2 não encontrado no arquivo!")
    
    # Aplicar correção 3
    if padrao3 in novo_conteudo:
        novo_conteudo = novo_conteudo.replace(padrao3, correcao3)
        logger.info("Correção 3 aplicada com sucesso!")
    else:
        logger.warning("Padrão 3 não encontrado no arquivo!")
    
    # Aplicar correção 4
    if padrao4 in novo_conteudo:
        novo_conteudo = novo_conteudo.replace(padrao4, correcao4)
        logger.info("Correção 4 aplicada com sucesso!")
    else:
        logger.warning("Padrão 4 não encontrado no arquivo!")
    
    # Salvar o arquivo com as correções
    try:
        with open(arquivo_path, 'w', encoding='utf-8') as file:
            file.write(novo_conteudo)
        logger.info(f"Arquivo {arquivo_path} atualizado com sucesso!")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar o arquivo: {e}")
        return False

if __name__ == "__main__":
    sucesso = aplicar_correcoes_fazenda()
    if sucesso:
        logger.info("Correções aplicadas com sucesso!")
    else:
        logger.error("Falha ao aplicar correções!")
