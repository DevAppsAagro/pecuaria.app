from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.db.models import Q, ExpressionWrapper, DecimalField, Sum
from django.utils import timezone
from decimal import Decimal
import json
from datetime import datetime, date, timedelta

# Importações dos modelos
from .models import (
    Animal, Lote, Pesagem, RateioCusto, Fazenda, CategoriaCusto, 
    Despesa, MovimentacaoNaoOperacional, Pasto, Benfeitoria, 
    ExtratoBancario, ManejoSanitario, ManejoReproducao
)
from .models_compras import Compra
from .models_vendas import Venda
from .models_abates import Abate
from .models_estoque import RateioMovimentacao

@login_required
def relatorios_view(request):
    return render(request, 'Relatorios/relatorios_list.html')

@login_required
def animais_por_lote(request, lote_id):
    animais = Animal.objects.filter(lote_id=lote_id, usuario=request.user).order_by('brinco_visual')
    dados = [{'id': animal.id, 'brinco_visual': animal.brinco_visual} for animal in animais]
    return JsonResponse(dados, safe=False)

@login_required
def relatorio_pesagens(request):
    # Obtém os parâmetros do filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    lote_id = request.GET.get('lote_id')
    animal_id = request.GET.get('animal_id')
    
    # Query base
    pesagens = Pesagem.objects.select_related('animal', 'animal__lote').filter(
        usuario=request.user
    ).order_by('-data')
    
    # Aplicar filtros se fornecidos
    if data_inicio:
        pesagens = pesagens.filter(data__gte=data_inicio)
    if data_fim:
        pesagens = pesagens.filter(data__lte=data_fim)
    if lote_id:
        pesagens = pesagens.filter(animal__lote_id=lote_id)
    if animal_id:
        pesagens = pesagens.filter(animal_id=animal_id)
    
    # Obtém lista de lotes para o filtro
    lotes = Lote.objects.filter(usuario=request.user)
    
    # Obtém lista de animais baseado no lote selecionado
    if lote_id:
        animais = Animal.objects.filter(lote_id=lote_id, usuario=request.user)
    else:
        animais = Animal.objects.filter(usuario=request.user)
    
    # Converte para lista e ordena por data decrescente (mais recente primeiro)
    pesagens = list(pesagens)
    
    # Adiciona o peso de entrada como primeira pesagem para cada animal
    animais_com_peso_entrada = set()
    for pesagem in pesagens:
        animal = pesagem.animal
        if animal.id not in animais_com_peso_entrada and animal.peso_entrada and animal.data_entrada:
            peso_entrada = Pesagem(
                animal=animal,
                peso=animal.peso_entrada,
                data=animal.data_entrada,
                usuario=request.user
            )
            pesagens.append(peso_entrada)
            animais_com_peso_entrada.add(animal.id)
    
    # Ordena todas as pesagens por data decrescente
    pesagens.sort(key=lambda x: x.data, reverse=True)
    
    dados_pesagens = []
    soma_ponderada_gmd = 0
    soma_dias = 0
    
    for i, pesagem in enumerate(pesagens):
        animal = pesagem.animal
        peso_atual = Decimal(str(pesagem.peso))
        
        # Dados básicos
        dados = {
            'data': pesagem.data,
            'animal': animal.brinco_visual,
            'peso': peso_atual,
            'arroba_atual': round(peso_atual / 30, 2),
            'gmd': 0,
            'ganho_kg': 0,
            'ganho_arroba': 0,
            'custo_arroba': 0,
            'abaixo_media': False,
            'percentual_abaixo': 0,
            'dias_periodo': 0,
            'variacao_percentual': 0
        }
        
        # Procura próxima pesagem do mesmo animal na lista
        proximas_pesagens = [p for p in pesagens[i+1:] if p.animal_id == animal.id]
        
        if proximas_pesagens:
            # Se tem pesagem anterior na lista (como está ordenado decrescente, a próxima é a anterior cronologicamente)
            pesagem_anterior = proximas_pesagens[0]
            dias = (pesagem.data - pesagem_anterior.data).days
            peso_anterior = Decimal(str(pesagem_anterior.peso))
        elif animal.peso_entrada and animal.data_entrada:
            # Se não tem pesagem anterior mas tem peso de entrada
            dias = (pesagem.data - animal.data_entrada).days
            peso_anterior = Decimal(str(animal.peso_entrada))
        else:
            dias = 0
            peso_anterior = 0
            
        if dias > 0:
            ganho_kg = peso_atual - peso_anterior
            gmd = round(ganho_kg / dias, 2)
            dados.update({
                'gmd': gmd,
                'ganho_kg': round(ganho_kg, 2),
                'ganho_arroba': round(ganho_kg / 30, 2),
                'dias_periodo': dias
            })
            if gmd > 0:
                soma_ponderada_gmd += (gmd * dias)
                soma_dias += dias
        
        # Calcula custo por arroba
        if animal.peso_entrada is not None:
            peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else 0
            ganho_total = peso_atual - peso_entrada
            
            if ganho_total > 0:
                kg_produzido = Decimal(str(peso_atual - peso_entrada))
                ganho_arroba = (kg_produzido / Decimal('15')) * Decimal('0.5')  # Restaurado cálculo original
                
                # Busca os custos dos rateios e saídas de estoque
                rateios = RateioCusto.objects.filter(animal=animal)
                custo_fixo = sum(Decimal(str(rateio.valor)) for rateio in rateios if rateio.item_despesa.categoria.tipo == 'fixo')
                custo_variavel = sum(Decimal(str(rateio.valor)) for rateio in rateios if rateio.item_despesa.categoria.tipo == 'variavel')
                
                # Adiciona custos das saídas de estoque
                custo_variavel += Decimal(str(animal.custo_variavel or '0'))
                
                custo_total = custo_fixo + custo_variavel
                
                if custo_total > 0 and ganho_arroba > 0:
                    custo_arroba = custo_total / ganho_arroba
                    dados['custo_arroba'] = round(float(custo_arroba), 2)
        
        dados_pesagens.append(dados)
    
    # Calcula a média ponderada do GMD
    media_gmd = round(soma_ponderada_gmd / soma_dias, 2) if soma_dias > 0 else None
    
    # Calcula a variação percentual para cada pesagem
    for i, dados in enumerate(dados_pesagens):
        if dados['gmd'] and dados['gmd'] > 0:  
            # Procura próximo GMD do mesmo animal
            proximos_dados = [d for d in dados_pesagens[i+1:] if d['animal'] == dados['animal'] and d['gmd'] and d['gmd'] > 0]
            if proximos_dados:
                gmd_anterior = proximos_dados[0]['gmd']
                if gmd_anterior > 0:
                    variacao = ((dados['gmd'] - gmd_anterior) / gmd_anterior) * 100
                    dados['percentual_variacao'] = round(variacao, 1)
                    dados['variacao_significativa'] = abs(variacao) > 15
                    dados['variacao_positiva'] = variacao > 15
                    dados['variacao_negativa'] = variacao < -15
    
    # Marca animais abaixo da média
    if media_gmd:  
        for dados in dados_pesagens:
            if dados['gmd'] and dados['gmd'] > 0 and dados['gmd'] < media_gmd:
                dados['abaixo_media'] = True
                dados['percentual_abaixo'] = round(((media_gmd - dados['gmd']) / media_gmd) * 100, 1)
                dados['variacao_percentual'] = round(((dados['gmd'] - media_gmd) / media_gmd) * 100, 1)
    
    # Inverte a ordem dos dados para a tabela (mais recentes primeiro)
    dados_pesagens.reverse()
    
    # Agrupa dados por data para calcular médias para os gráficos
    dados_por_data = {}
    for dados in dados_pesagens:
        data = dados['data'].strftime('%d/%m/%Y')
        if data not in dados_por_data:
            dados_por_data[data] = {
                'pesos': [],
                'gmd': [],
                'custos': []
            }
        
        dados_por_data[data]['pesos'].append(float(dados['peso']))
        if dados['gmd'] > 0:
            dados_por_data[data]['gmd'].append(float(dados['gmd']))
        if dados.get('custo_arroba', 0) > 0:
            dados_por_data[data]['custos'].append(float(dados['custo_arroba']))
    
    # Calcula médias por data para os gráficos - mantém ordem cronológica
    datas = sorted(dados_por_data.keys())
    medias_peso = []
    medias_gmd = []
    medias_custo = []
    
    for data in datas:
        dados_data = dados_por_data[data]
        
        # Média dos pesos
        if dados_data['pesos']:
            medias_peso.append(round(sum(dados_data['pesos']) / len(dados_data['pesos']), 2))
        else:
            medias_peso.append(0)
        
        # Média do GMD
        if dados_data['gmd']:
            medias_gmd.append(round(sum(dados_data['gmd']) / len(dados_data['gmd']), 2))
        else:
            medias_gmd.append(0)
        
        # Média dos custos
        if dados_data['custos']:
            medias_custo.append(round(sum(dados_data['custos']) / len(dados_data['custos']), 2))
        else:
            medias_custo.append(0)
    
    # Dados para os gráficos
    dados_graficos = {
        'datas': datas,
        'pesos': medias_peso,
        'gmd': medias_gmd,
        'custos': medias_custo
    }
    
    # Calcular dados para os cards de resumo
    ganho_total = dados_pesagens[-1]['peso'] - dados_pesagens[0]['peso'] if dados_pesagens else 0
    
    # Calcula média do GMD apenas para valores válidos
    gmds_validos = [d['gmd'] for d in dados_pesagens if d['gmd'] and d['gmd'] > 0]
    media_gmd = round(sum(gmds_validos) / len(gmds_validos), 2) if gmds_validos else 0
    
    # Calcula custo médio apenas para valores válidos
    custos_validos = [d['custo_arroba'] for d in dados_pesagens if d['custo_arroba'] and d['custo_arroba'] > 0]
    custo_medio = round(sum(custos_validos) / len(custos_validos), 2) if custos_validos else 0
    
    # Calcular projeção para meta (exemplo: meta de 500kg)
    meta = 500
    if dados_pesagens and media_gmd > 0:
        peso_atual = dados_pesagens[-1]['peso']
        peso_faltante = meta - peso_atual
        dias_para_meta = int(peso_faltante / media_gmd) if peso_faltante > 0 else 0
    else:
        dias_para_meta = None

    context = {
        'dados_pesagens': dados_pesagens,
        'dados_graficos': dados_graficos,
        'lotes': lotes,
        'animais': animais,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'lote_id': lote_id,
            'animal_id': animal_id
        },
        'ganho_total': ganho_total,
        'media_gmd': media_gmd,
        'custo_medio': custo_medio,
        'dias_para_meta': dias_para_meta
    }
    
    return render(request, 'Relatorios/pesagens.html', context)

@login_required
def relatorio_confinamento(request):
    # Por enquanto retornamos apenas o template com dados fictícios
    # Posteriormente implementaremos a lógica real
    return render(request, 'Relatorios/relatorio_confinamento.html')

@login_required
def relatorio_dre(request):
    """
    Página do DRE (Demonstrativo de Resultados do Exercício)
    """
    # Obter fazendas do usuário para filtro
    fazendas = Fazenda.objects.filter(usuario=request.user)
    
    # Filtros
    data_inicial_str = request.GET.get('data_inicial')
    data_final_str = request.GET.get('data_final')
    fazenda_id = request.GET.get('fazenda_id')
    
    # Dados do relatório
    dados_dre = None
    if data_inicial_str and data_final_str:
        # Processar filtros e obter dados do relatório (função atualizar_dre_dados)
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            dados_dre = atualizar_dre_dados(request.user, data_inicial, data_final, fazenda_id)
        except ValueError as e:
            print(f"Erro ao processar datas: {e}")
    
    context = {
        'fazendas': fazendas,
        'dados_dre': dados_dre,
        'filtros': {
            'data_inicial': data_inicial_str,
            'data_final': data_final_str,
            'fazenda_id': fazenda_id,
        }
    }
    
    return render(request, 'Relatorios/dre.html', context)

def atualizar_dre_dados(usuario, data_inicial, data_final, fazenda_id=None):
    """
    Função auxiliar para processar os dados do DRE
    """
    print(f"Período: {data_inicial} a {data_final}")
    print(f"Fazenda ID: {fazenda_id}")

    # PARTE 1: DADOS PARA RESULTADO OPERACIONAL
    
    # 1.1 RECEITAS OPERACIONAIS: Abates
    # Busca direto na tabela Abate com filtro por data
    receitas_abates = 0
    if data_inicial and data_final:
        filtro_abates = {'data__range': [data_inicial, data_final], 'usuario': usuario}
        if fazenda_id:
            # Filtro da fazenda é aplicado nos animais
            abates = Abate.objects.filter(usuario=usuario, data__range=[data_inicial, data_final])
            total_abate = 0
            for abate in abates:
                # Verifica a fazenda nos animais abatidos
                for animal_abate in abate.animais.all():
                    if animal_abate.animal.fazenda_atual_id == int(fazenda_id):
                        total_abate += float(animal_abate.valor_total)
            receitas_abates = float(total_abate)
        else:
            # Sem filtro de fazenda, computa o valor total dos abates manualmente
            abates = Abate.objects.filter(
                usuario=usuario, 
                data__range=[data_inicial, data_final]
            )
            
            total_abate = 0
            for abate in abates:
                # Calcular o total manualmente em vez de usar o property
                abate_total = abate.animais.aggregate(total=Sum('valor_total'))['total'] or 0
                total_abate += float(abate_total)
                
            receitas_abates = float(total_abate)

    # 1.2 RECEITAS OPERACIONAIS: Vendas
    # Busca direto na tabela Venda com filtro por data
    receitas_vendas = 0
    if data_inicial and data_final:
        filtro_vendas = {'data__range': [data_inicial, data_final], 'usuario': usuario}
        if fazenda_id:
            # Filtro da fazenda é aplicado nos animais
            vendas = Venda.objects.filter(usuario=usuario, data__range=[data_inicial, data_final])
            total_venda = 0
            for venda in vendas:
                # Verifica a fazenda nos animais vendidos
                for animal_venda in venda.animais.all():
                    if animal_venda.animal.fazenda_atual_id == int(fazenda_id):
                        total_venda += float(animal_venda.valor_total)
            receitas_vendas = float(total_venda)
        else:
            # Sem filtro de fazenda, computa o valor total das vendas manualmente
            vendas = Venda.objects.filter(
                usuario=usuario, 
                data__range=[data_inicial, data_final]
            )
            
            total_venda = 0
            for venda in vendas:
                # Calcular o total manualmente em vez de usar o property
                venda_total = venda.animais.aggregate(total=Sum('valor_total'))['total'] or 0
                total_venda += float(venda_total)
                
            receitas_vendas = float(total_venda)
    
    # Total das receitas operacionais
    receitas_totais = float(receitas_abates + receitas_vendas)
    
    # Converter para float para evitar problemas de tipo em operações posteriores
    receitas_totais_float = float(receitas_totais)
    receitas_abates_float = float(receitas_abates)
    receitas_vendas_float = float(receitas_vendas)

    # Percentuais das receitas
    percentual_abate = (receitas_abates_float / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    percentual_vendas = (receitas_vendas_float / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0

    # 2. CUSTOS OPERACIONAIS
    # 2.1 CUSTOS FIXOS (Despesas com categorias fixas)
    # Busca através de ItemDespesa com filtro por tipo de categoria "FIXO"
    filtro_despesas_fixas = {
        'usuario': usuario,
        'data_emissao__range': [data_inicial, data_final], 
        'itens__categoria__tipo': 'fixo'  
    }
    if fazenda_id:
        filtro_despesas_fixas['itens__fazenda_destino_id'] = fazenda_id

    # Agrupar por categoria
    custos_fixos_por_categoria = Despesa.objects.filter(**filtro_despesas_fixas).values(
        'itens__categoria__nome', 'itens__categoria_id'
    ).annotate(
        total=Sum('itens__valor_total')
    ).order_by('itens__categoria__nome')

    # Detalhar as subcategorias
    custos_fixos = []
    total_custos_fixos = 0

    for categoria in custos_fixos_por_categoria:
        valor_categoria = float(categoria['total'])
        total_custos_fixos += valor_categoria
        
        # Buscar subcategorias (itens de despesa agrupados)
        filtro_subcategoria = {
            'data_emissao__range': [data_inicial, data_final],
            'usuario': usuario,
            'itens__categoria_id': categoria['itens__categoria_id']
        }
        if fazenda_id:
            filtro_subcategoria['itens__fazenda_destino_id'] = fazenda_id
            
        subcategorias = Despesa.objects.filter(**filtro_subcategoria).values(
            'itens__subcategoria__nome'
        ).annotate(
            total=Sum('itens__valor_total')
        ).order_by('-total')
        
        subcategorias_formatadas = []
        for sub in subcategorias:
            subcategorias_formatadas.append({
                'nome': sub['itens__subcategoria__nome'],
                'valor': float(sub['total']),
                'percentual': (float(sub['total']) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
            })
        
        # Adicionar categoria com suas subcategorias
        custos_fixos.append({
            'nome': categoria['itens__categoria__nome'],
            'valor': float(valor_categoria),
            'percentual': (float(valor_categoria) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0,
            'subcategorias': subcategorias_formatadas
        })

    # 2.2 CUSTOS VARIÁVEIS (Despesas com categorias variáveis)
    # Busca através de ItemDespesa com filtro por tipo de categoria "VARIÁVEL"
    filtro_despesas_variaveis = {
        'usuario': usuario,
        'data_emissao__range': [data_inicial, data_final], 
        'itens__categoria__tipo': 'variavel'  
    }
    if fazenda_id:
        filtro_despesas_variaveis['itens__fazenda_destino_id'] = fazenda_id

    # Agrupar por categoria
    custos_variaveis_por_categoria = Despesa.objects.filter(**filtro_despesas_variaveis).values(
        'itens__categoria__nome', 'itens__categoria_id'
    ).annotate(
        total=Sum('itens__valor_total')
    ).order_by('itens__categoria__nome')

    # Detalhar as subcategorias
    custos_variaveis = []
    total_custos_variaveis = 0

    for categoria in custos_variaveis_por_categoria:
        valor_categoria = float(categoria['total'])
        total_custos_variaveis += valor_categoria
        
        # Buscar subcategorias (itens de despesa agrupados)
        filtro_subcategoria = {
            'data_emissao__range': [data_inicial, data_final],
            'usuario': usuario,
            'itens__categoria_id': categoria['itens__categoria_id']
        }
        if fazenda_id:
            filtro_subcategoria['itens__fazenda_destino_id'] = fazenda_id
            
        subcategorias = Despesa.objects.filter(**filtro_subcategoria).values(
            'itens__subcategoria__nome'
        ).annotate(
            total=Sum('itens__valor_total')
        ).order_by('-total')
        
        subcategorias_formatadas = []
        for sub in subcategorias:
            subcategorias_formatadas.append({
                'nome': sub['itens__subcategoria__nome'],
                'valor': float(sub['total']),
                'percentual': (float(sub['total']) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
            })
        
        # Adicionar categoria com suas subcategorias
        custos_variaveis.append({
            'nome': categoria['itens__categoria__nome'],
            'valor': float(valor_categoria),
            'percentual': (float(valor_categoria) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0,
            'subcategorias': subcategorias_formatadas
        })
        
    # Total dos custos
    total_custos_fixos = float(total_custos_fixos)
    total_custos_variaveis = float(total_custos_variaveis)
    total_geral_custos = float(total_custos_fixos + total_custos_variaveis)
    
    # Percentuais dos custos
    percentual_custos_fixos = (total_custos_fixos / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    percentual_custos_variaveis = (total_custos_variaveis / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    percentual_geral_custos = (total_geral_custos / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # 3. RESULTADO OPERACIONAL
    receitas_totais = float(receitas_totais)
    total_geral_custos = float(total_geral_custos)
    resultado_operacional = float(receitas_totais - total_geral_custos)
    percentual_resultado = (resultado_operacional / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # PARTE 2: DADOS PARA INVESTIMENTOS E RESULTADOS NÃO OPERACIONAIS
    
    # 4. INVESTIMENTOS (Compra de animais e categorias de despesa do tipo "INVESTIMENTO")
    # 4.1 COMPRA DE ANIMAIS
    filtro_compras = {
        'data__range': [data_inicial, data_final],
        'usuario': usuario
    }
    
    # Compras não têm campo 'fazenda' diretamente, então não podemos filtrar por fazenda neste nível
    compras = Compra.objects.filter(**filtro_compras)
    
    # Filtramos os animais comprados depois por fazenda, se necessário
    total_compra_animais = 0
    for compra in compras:
        compra_total = 0
        # Se temos um filtro de fazenda, verificamos se os animais estão nessa fazenda
        if fazenda_id:
            for animal_compra in compra.animais.all():
                if animal_compra.animal.fazenda_atual_id == fazenda_id:
                    compra_total += float(animal_compra.valor_total or 0)
        else:
            # Sem filtro de fazenda, somamos todos
            compra_total = compra.animais.aggregate(total=Sum('valor_total'))['total'] or 0
            
        total_compra_animais += float(compra_total)
    
    # Percentual de compra de animais em relação às receitas
    percentual_compra_animais = (float(total_compra_animais) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # 4.2 OUTROS INVESTIMENTOS (Categorias de despesa marcadas como Investimento)
    filtro_investimentos = {
        'data_emissao__range': [data_inicial, data_final], 
        'usuario': usuario,
        'itens__categoria__tipo': 'investimento'  
    }
    if fazenda_id:
        filtro_investimentos['itens__fazenda_destino_id'] = fazenda_id
        
    # Agrupar por categoria
    investimentos_por_categoria = Despesa.objects.filter(**filtro_investimentos).values(
        'itens__categoria__nome', 'itens__categoria_id'
    ).annotate(
        total=Sum('itens__valor_total')
    ).order_by('itens__categoria__nome')
    
    # Detalhar as subcategorias dos investimentos
    investimentos = []
    total_investimentos_outros = 0
    
    # Item especial para compra de animais
    if total_compra_animais > 0:
        investimentos.append({
            'nome': 'Compra de Animais',
            'valor': float(total_compra_animais),
            'percentual': percentual_compra_animais,
            'subcategorias': []  
        })
    
    for categoria in investimentos_por_categoria:
        valor_categoria = float(categoria['total'])
        total_investimentos_outros += float(valor_categoria)
        
        # Buscar subcategorias (itens de despesa agrupados)
        filtro_subcategoria = {
            'data_emissao__range': [data_inicial, data_final],
            'usuario': usuario,
            'itens__categoria_id': categoria['itens__categoria_id']
        }
        if fazenda_id:
            filtro_subcategoria['itens__fazenda_destino_id'] = fazenda_id
            
        subcategorias = Despesa.objects.filter(**filtro_subcategoria).values(
            'itens__subcategoria__nome'
        ).annotate(
            total=Sum('itens__valor_total')
        ).order_by('-total')
        
        subcategorias_formatadas = []
        for sub in subcategorias:
            subcategorias_formatadas.append({
                'nome': sub['itens__subcategoria__nome'],
                'valor': float(sub['total']),
                'percentual': (float(sub['total']) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
            })
        
        # Adicionar categoria com suas subcategorias
        investimentos.append({
            'nome': categoria['itens__categoria__nome'],
            'valor': float(valor_categoria),
            'percentual': (float(valor_categoria) / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0,
            'subcategorias': subcategorias_formatadas
        })
    
    # Total dos investimentos
    total_investimentos = float(total_compra_animais) + float(total_investimentos_outros)
    percentual_investimentos = (total_investimentos / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # 5. NÃO OPERACIONAL (Movimentações financeiras não operacionais)
    filtro_nao_op = {
        'data__range': [data_inicial, data_final],
        'usuario': usuario
    }
    if fazenda_id:
        filtro_nao_op['fazenda_id'] = fazenda_id
    
    # Receitas não operacionais (entradas)
    receitas_nao_op = MovimentacaoNaoOperacional.objects.filter(
        **filtro_nao_op, tipo='entrada'
    ).aggregate(
        total=Sum('valor')
    )['total'] or 0
    receitas_nao_op = float(receitas_nao_op)
    
    # Despesas não operacionais (saídas)
    despesas_nao_op = MovimentacaoNaoOperacional.objects.filter(
        **filtro_nao_op, tipo='saida'
    ).aggregate(
        total=Sum('valor')
    )['total'] or 0
    despesas_nao_op = float(despesas_nao_op)
    
    # Resultado não operacional
    resultado_nao_op = float(receitas_nao_op) - float(despesas_nao_op)
    
    # Percentuais não operacionais
    percentual_receitas_nao_op = (receitas_nao_op / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    percentual_despesas_nao_op = (despesas_nao_op / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    percentual_resultado_nao_op = (resultado_nao_op / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # RESULTADO FINAL (EBITDA)
    resultado_final = float(resultado_operacional) - float(total_investimentos) + float(resultado_nao_op)
    percentual_resultado_final = (resultado_final / receitas_totais_float) * 100 if receitas_totais_float > 0 else 0
    
    # Montar resposta
    dados_dre = {
        # 1. RECEITAS
        'receitas_abates': receitas_abates,
        'receitas_vendas': receitas_vendas,
        'receitas_totais': receitas_totais,
        'percentual_abate': percentual_abate,
        'percentual_vendas': percentual_vendas,
        
        # 2. CUSTOS
        'custos_fixos': custos_fixos,
        'custos_variaveis': custos_variaveis,
        'total_custos_fixos': float(total_custos_fixos),
        'total_custos_variaveis': float(total_custos_variaveis),
        'total_geral_custos': float(total_geral_custos),
        'percentual_custos_fixos': percentual_custos_fixos,
        'percentual_custos_variaveis': percentual_custos_variaveis,
        'percentual_geral_custos': percentual_geral_custos,
        
        # 3. RESULTADO OPERACIONAL
        'resultado_operacional': float(resultado_operacional),
        'percentual_resultado': percentual_resultado,
        
        # 4. INVESTIMENTOS
        'total_compra_animais': float(total_compra_animais),
        'percentual_compra_animais': percentual_compra_animais,
        'investimentos': investimentos,
        'total_investimentos_outros': float(total_investimentos_outros),
        'total_investimentos': float(total_investimentos),
        'percentual_investimentos': percentual_investimentos,
        
        # 5. NÃO OPERACIONAL
        'receitas_nao_op': float(receitas_nao_op),
        'percentual_receitas_nao_op': percentual_receitas_nao_op,
        'despesas_nao_op': float(despesas_nao_op),
        'percentual_despesas_nao_op': percentual_despesas_nao_op,
        'resultado_nao_op': float(resultado_nao_op),
        'percentual_resultado_nao_op': percentual_resultado_nao_op,
        
        # RESULTADO FINAL
        'resultado_final': resultado_final,
        'percentual_resultado_final': percentual_resultado_final,
    }
    
    return dados_dre

@login_required
def atualizar_dre(request):
    """
    Função simplificada para obter dados do DRE diretamente das tabelas.
    - Receitas: Vendas e Abates
    - Custos: Fixos e Variáveis das Despesas
    - Investimentos: Compra de animais e investimentos por categoria
    - Não Operacional: Entradas e saídas não operacionais
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Dados recebidos: {data}")
            
            # Parâmetros do filtro
            fazenda_id = data.get('fazenda_id')
            data_inicial_str = data.get('data_inicial')
            data_final_str = data.get('data_final')
            
            # Validar e converter datas
            if not data_inicial_str or not data_final_str:
                return JsonResponse({
                    'success': False, 
                    'error': 'Datas inicial e final são obrigatórias'
                })
            
            try:
                data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
                data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Formato de data inválido'
                })
            
            # Obter dados do DRE
            dados_dre = atualizar_dre_dados(request.user, data_inicial, data_final, fazenda_id)
            
            # Adicionar campo de sucesso para a API
            dados_dre['success'] = True
            
            return JsonResponse(dados_dre)
            
        except Exception as e:
            print(f"Erro ao processar DRE: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Método não permitido'
        })

@login_required
def atualizar_dre_dados_ajax(request):
    """
    Endpoint AJAX para obter os dados do DRE para o dashboard financeiro
    """
    usuario = request.user
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')
    fazenda_id = request.GET.get('fazenda_id')
    
    # Converter strings de data para objetos datetime
    try:
        data_inicial_dt = datetime.strptime(data_inicial, '%Y-%m-%d')
        data_final_dt = datetime.strptime(data_final, '%Y-%m-%d')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Formato de data inválido'}, status=400)
    
    # Obter dados do DRE
    dre_dados = atualizar_dre_dados(usuario, data_inicial, data_final, fazenda_id)
    
    # Processar dados para formato mensal (para o gráfico)
    receitas_mensais = {}
    custos_mensais = {}
    
    # Calcular o número de meses entre as datas
    num_meses = (data_final_dt.year - data_inicial_dt.year) * 12 + data_final_dt.month - data_inicial_dt.month + 1
    
    # Inicializar dicionários para cada mês no período
    current_date = data_inicial_dt
    for _ in range(num_meses):
        month_key = current_date.strftime('%b/%Y')
        receitas_mensais[month_key] = 0
        custos_mensais[month_key] = 0
        current_date += relativedelta(months=1)
    
    # Processar receitas
    for receita in dre_dados.get('receitas', []):
        try:
            data_receita = datetime.strptime(receita.get('data', ''), '%Y-%m-%d')
            if data_inicial_dt <= data_receita <= data_final_dt:
                month_key = data_receita.strftime('%b/%Y')
                receitas_mensais[month_key] += float(receita.get('valor', 0))
        except (ValueError, TypeError):
            continue
    
    # Processar custos
    for categoria in dre_dados.get('categorias_custos', []):
        for custo in categoria.get('custos', []):
            try:
                data_custo = datetime.strptime(custo.get('data', ''), '%Y-%m-%d')
                if data_inicial_dt <= data_custo <= data_final_dt:
                    month_key = data_custo.strftime('%b/%Y')
                    custos_mensais[month_key] += float(custo.get('valor', 0))
            except (ValueError, TypeError):
                continue
    
    # Calcular totais
    receitas_totais = sum(receitas_mensais.values())
    custos_totais = sum(custos_mensais.values())
    
    # Calcular lucro e margem
    lucro = receitas_totais - custos_totais
    margem = 0 if receitas_totais == 0 else round((lucro / receitas_totais) * 100, 2)
    
    # Preparar dados de distribuição de custos por categoria
    categorias_custos = []
    valores_custos = []
    
    for categoria in dre_dados.get('categorias_custos', []):
        nome_categoria = categoria.get('nome', 'Sem categoria')
        total_categoria = categoria.get('total', 0)
        
        if total_categoria > 0:  # Apenas incluir categorias com valores
            categorias_custos.append(nome_categoria)
            valores_custos.append(float(total_categoria))
    
    # Ordenar por valor (maior para menor) e limitar a 8 categorias
    if categorias_custos:
        # Criar pares (categoria, valor) e ordenar
        pares_ordenados = sorted(zip(categorias_custos, valores_custos), key=lambda x: x[1], reverse=True)
        
        # Se houver mais de 8 categorias, consolidar o restante em "Outros"
        if len(pares_ordenados) > 8:
            top_categorias = pares_ordenados[:7]
            outros_valor = sum(valor for _, valor in pares_ordenados[7:])
            
            # Desempacotar os pares ordenados de volta para as listas
            categorias_custos, valores_custos = zip(*top_categorias)
            categorias_custos = list(categorias_custos)
            valores_custos = list(valores_custos)
            
            # Adicionar a categoria "Outros"
            if outros_valor > 0:
                categorias_custos.append("Outros")
                valores_custos.append(outros_valor)
        else:
            # Desempacotar os pares ordenados
            categorias_custos, valores_custos = zip(*pares_ordenados)
            categorias_custos = list(categorias_custos)
            valores_custos = list(valores_custos)
    
    # Formatar valores monetários para exibição
    def formatar_valor(valor):
        return f"{valor:,.2f}".replace(',', '.').replace('.', ',')
    
    # Preparar resposta JSON
    response_data = {
        'receitas_mensais': receitas_mensais,
        'custos_mensais': custos_mensais,
        'receitas_totais': formatar_valor(receitas_totais),
        'custos_totais': formatar_valor(custos_totais),
        'lucro': formatar_valor(lucro),
        'margem': str(margem),
        'categorias_custos': categorias_custos,
        'valores_custos': valores_custos,
    }
    
    return JsonResponse(response_data)
