from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Animal, Lote, Pesagem, RateioCusto
from .models_estoque import RateioMovimentacao
from decimal import Decimal

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
