from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Prefetch
from .models import Animal, Lote, Pesagem, RateioCusto
from .models_estoque import RateioMovimentacao
from decimal import Decimal
from datetime import timedelta

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
    
    # Query base otimizada
    pesagens = Pesagem.objects.select_related(
        'animal',
        'animal__lote',
        'animal__categoria_animal',
        'animal__raca'
    ).filter(
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
    
    # Limita o número de registros para evitar timeout
    pesagens = pesagens[:500]
    
    # Obtém lista de lotes e animais para o filtro
    lotes = Lote.objects.filter(usuario=request.user)
    if lote_id:
        animais = Animal.objects.filter(lote_id=lote_id, usuario=request.user)
    else:
        animais = Animal.objects.filter(usuario=request.user)
    
    # Converte para lista e adiciona peso de entrada
    pesagens = list(pesagens)
    animais_processados = set()
    
    for pesagem in pesagens:
        animal = pesagem.animal
        if animal.id not in animais_processados and animal.peso_entrada and animal.data_entrada:
            peso_entrada = Pesagem(
                animal=animal,
                peso=animal.peso_entrada,
                data=animal.data_entrada,
                usuario=request.user
            )
            pesagens.append(peso_entrada)
            animais_processados.add(animal.id)
    
    # Ordena todas as pesagens por data decrescente
    pesagens.sort(key=lambda x: x.data, reverse=True)
    
    # Pré-calcula os custos por animal para evitar múltiplas queries
    custos_por_animal = {}
    animais_ids = {p.animal.id for p in pesagens}
    rateios = RateioCusto.objects.filter(animal_id__in=animais_ids).select_related('item_despesa__categoria')
    
    for animal_id in animais_ids:
        rateios_animal = [r for r in rateios if r.animal_id == animal_id]
        custo_fixo = sum(Decimal(str(r.valor)) for r in rateios_animal if r.item_despesa.categoria.tipo == 'fixo')
        custo_variavel = sum(Decimal(str(r.valor)) for r in rateios_animal if r.item_despesa.categoria.tipo == 'variavel')
        custos_por_animal[animal_id] = (custo_fixo, custo_variavel)
    
    dados_pesagens = []
    soma_ponderada_gmd = Decimal('0')
    soma_dias = 0
    
    for i, pesagem in enumerate(pesagens):
        animal = pesagem.animal
        peso_atual = Decimal(str(pesagem.peso))
        
        dados = {
            'data': pesagem.data,
            'animal': animal.brinco_visual,
            'peso': peso_atual,
            'arroba_atual': round(peso_atual / 30, 2),
            'gmd': 0,
            'ganho_kg': 0,
            'ganho_arroba': 0,
            'custo_arroba': 0,
            'dias_periodo': 0,
            'variacao_percentual': 0
        }
        
        # Procura próxima pesagem do mesmo animal
        proximas_pesagens = [p for p in pesagens[i+1:] if p.animal_id == animal.id]
        
        if proximas_pesagens:
            pesagem_anterior = proximas_pesagens[0]
            dias = (pesagem.data - pesagem_anterior.data).days
            peso_anterior = Decimal(str(pesagem_anterior.peso))
        elif animal.peso_entrada and animal.data_entrada:
            dias = (pesagem.data - animal.data_entrada).days
            peso_anterior = Decimal(str(animal.peso_entrada))
        else:
            dias = 0
            peso_anterior = Decimal('0')
        
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
                soma_ponderada_gmd += (Decimal(str(gmd)) * Decimal(str(dias)))
                soma_dias += dias
        
        # Calcula custo por arroba usando os custos pré-calculados
        if animal.peso_entrada is not None:
            peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else Decimal('0')
            ganho_total = peso_atual - peso_entrada
            
            if ganho_total > 0:
                kg_produzido = peso_atual - peso_entrada
                ganho_arroba = (kg_produzido / Decimal('15')) * Decimal('0.5')
                
                if animal.id in custos_por_animal:
                    custo_fixo, custo_variavel = custos_por_animal[animal.id]
                    custo_variavel += Decimal(str(animal.custo_variavel or '0'))
                    custo_total = custo_fixo + custo_variavel
                    
                    if custo_total > 0 and ganho_arroba > 0:
                        custo_arroba = custo_total / ganho_arroba
                        dados['custo_arroba'] = round(float(custo_arroba), 2)
        
        dados_pesagens.append(dados)
    
    # Calcula a média ponderada do GMD
    media_gmd = round(soma_ponderada_gmd / Decimal(str(soma_dias)), 2) if soma_dias > 0 else None
    
    # Calcula variações percentuais
    for i, dados in enumerate(dados_pesagens):
        if dados['gmd'] and dados['gmd'] > 0:
            proximos_dados = [d for d in dados_pesagens[i+1:] if d['animal'] == dados['animal'] and d['gmd'] and d['gmd'] > 0]
            if proximos_dados:
                gmd_anterior = proximos_dados[0]['gmd']
                if gmd_anterior > 0:
                    variacao = ((dados['gmd'] - gmd_anterior) / gmd_anterior) * 100
                    dados['percentual_variacao'] = round(variacao, 1)
                    dados['variacao_positiva'] = variacao > 15
                    dados['variacao_negativa'] = variacao < -15
    
    # Prepara dados para os gráficos
    dados_graficos = {
        'datas': [],
        'pesos': [],
        'gmd': [],
        'custos': []
    }
    
    # Agrupa por data para os gráficos (limita a 30 pontos)
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
    
    # Pega apenas os últimos 30 pontos para os gráficos
    datas = sorted(dados_por_data.keys())[-30:]
    
    for data in datas:
        dados_data = dados_por_data[data]
        if dados_data['pesos']:
            dados_graficos['datas'].append(data)
            dados_graficos['pesos'].append(round(sum(dados_data['pesos']) / len(dados_data['pesos']), 2))
        if dados_data['gmd']:
            dados_graficos['gmd'].append(round(sum(dados_data['gmd']) / len(dados_data['gmd']), 2))
        if dados_data['custos']:
            dados_graficos['custos'].append(round(sum(dados_data['custos']) / len(dados_data['custos']), 2))
    
    context = {
        'dados_pesagens': dados_pesagens,
        'dados_graficos': dados_graficos,
        'media_gmd': media_gmd,
        'lotes': lotes,
        'animais': animais,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'lote_id': lote_id,
            'animal_id': animal_id
        }
    }
    
    return render(request, 'Relatorios/pesagens.html', context)
