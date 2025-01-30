from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from .models import Animal, Pesagem, ManejoSanitario, MovimentacaoAnimal, RateioCusto, Lote
from .models_compras import CompraAnimal, Compra
from .models_vendas import VendaAnimal
from .models_abates import AbateAnimal
from django.db.models import Sum, F
from core.models import Despesa, Contato, Fazenda

@login_required
def imprimir_animal(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    
    # Busca informações de abate e venda
    abate_animal = AbateAnimal.objects.filter(animal=animal).first()
    venda = VendaAnimal.objects.filter(animal=animal).first()
    
    # Calcula dias ativos - usa data de saída se existir, senão usa hoje
    data_entrada = animal.data_entrada
    if abate_animal:
        data_final = abate_animal.abate.data
    elif venda:
        data_final = venda.data
    else:
        data_final = timezone.now().date()
    
    dias_ativos = (data_final - data_entrada).days if data_entrada else 0
    
    # Pega a última pesagem
    ultima_pesagem = animal.pesagens.order_by('-data').first()
    
    # Calcula peso atual e @ atual
    peso_atual = ultima_pesagem.peso if ultima_pesagem else None
    arroba_atual = None
    if peso_atual:
        # Se tem abate, usa o rendimento do abate, senão usa 50%
        rendimento = Decimal(str(abate_animal.rendimento)) / Decimal('100') if abate_animal else Decimal('0.5')
        arroba_atual = (Decimal(str(peso_atual)) * rendimento / Decimal('15'))
    
    # Calcula @ de entrada (sempre usa 50% de rendimento na entrada)
    peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else 0
    arroba_entrada = (peso_entrada * Decimal('0.5') / Decimal('15'))

    # Calcula ganho em @
    ganho_arroba = Decimal(str(arroba_atual - arroba_entrada)) if arroba_atual else None

    # Calcula o GMD (Ganho Médio Diário)
    gmd = 0
    ganho_peso = 0
    if peso_atual and animal.peso_entrada and dias_ativos > 0:
        ganho_peso = peso_atual - animal.peso_entrada
        gmd = round(ganho_peso / dias_ativos, 3)

    # Calcula custos
    rateios = RateioCusto.objects.filter(animal=animal)
    custos_fixos_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'fixo')
    custos_variaveis_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'variavel')
    custos_variaveis_totais += animal.custo_variavel or 0
    custos_total = Decimal(str(custos_fixos_totais)) + Decimal(str(custos_variaveis_totais))

    # Calcula custos por kg e por @
    custo_por_kg = 0
    custo_por_arroba = 0
    
    if animal.peso_entrada is not None and ultima_pesagem and ganho_arroba and ganho_arroba > 0:
        ganho_total = Decimal(str(peso_atual)) - Decimal(str(animal.peso_entrada))
        
        if custos_total > 0:
            # Calcula custo por kg (custo total / kg produzido)
            custo_por_kg = float(custos_total / ganho_total)
            # Calcula custo por @ (custo total / @ produzida)
            custo_por_arroba = float(custos_total / ganho_arroba)

    # Calcula custos diários
    if dias_ativos > 0:
        custo_diario = custos_total / Decimal(str(dias_ativos))
        custo_variavel_diario = Decimal(str(custos_variaveis_totais)) / dias_ativos
        custo_fixo_diario = Decimal(str(custos_fixos_totais)) / dias_ativos
    else:
        custo_diario = Decimal('0')
        custo_variavel_diario = Decimal('0')
        custo_fixo_diario = Decimal('0')

    # Informações de abate/venda
    valor_entrada = animal.valor_compra or 0
    
    # Busca informações de compra
    compra_animal = CompraAnimal.objects.filter(animal=animal).first()
    
    peso_final = 0
    valor_saida = 0
    arrobas_final = 0
    lucro = 0

    # Busca informações de abate
    if abate_animal:
        peso_final = abate_animal.peso_vivo
        valor_saida = abate_animal.valor_total
        # Calcula arrobas considerando o rendimento de carcaça
        rendimento_carcaca = Decimal(str(abate_animal.rendimento)) / Decimal('100')
        arrobas_final = (peso_final * rendimento_carcaca / Decimal('15')) if peso_final else 0
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    elif venda:
        peso_final = venda.peso
        valor_saida = venda.valor_total
        arrobas_final = peso_final / Decimal('30')  # Venda usa rendimento padrão de 50%
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    else:
        peso_final = ultima_pesagem.peso if ultima_pesagem else peso_atual
        arrobas_final = peso_final / Decimal('30') if peso_final else 0

    # Buscar históricos
    pesagens = Pesagem.objects.filter(animal=animal).order_by('-data')
    manejos = ManejoSanitario.objects.filter(animal=animal).order_by('-data')
    movimentacoes = MovimentacaoAnimal.objects.filter(animal=animal).order_by('-data_movimentacao')
    
    # Informações do cabeçalho
    cabecalho = {
        'empresa': 'FAZENDA MODELO LTDA',
        'cnpj': '12.345.678/0001-90',
        'endereco': 'Rodovia BR 101, Km 123',
        'cidade_uf': 'Cidade Alta - MT',
        'telefone': '(11) 1234-5678',
        'email': 'contato@fazendamodelo.com.br'
    }
    
    # Informações do rodapé
    rodape = {
        'responsavel_tecnico': 'Dr. João Silva',
        'crmv': 'CRMV-MT 12345',
        'sistema': 'Sistema de Gestão Pecuária v1.0'
    }
    
    context = {
        'animal': animal,
        'dias_ativos': dias_ativos,
        'compra': compra_animal,
        'venda': venda,
        'abate': abate_animal,
        'arrobas_final': arrobas_final,
        'pesagens': pesagens,
        'manejos': manejos,
        'movimentacoes': movimentacoes,
        'peso_atual': peso_atual,
        'arroba_atual': arroba_atual,
        'arroba_entrada': arroba_entrada,
        'ganho_arroba': ganho_arroba,
        'custo_total': custos_total,
        'custos_fixos_totais': custos_fixos_totais,
        'custos_variaveis_totais': custos_variaveis_totais,
        'custo_por_kg': custo_por_kg,
        'custo_por_arroba': custo_por_arroba,
        'custo_diario': custo_diario,
        'custo_fixo_diario': custo_fixo_diario,
        'custo_variavel_diario': custo_variavel_diario,
        'lucro': lucro,
        'gmd': gmd,
        'cabecalho': cabecalho,
        'rodape': rodape,
    }
    
    return render(request, 'impressao/animal_detail_print.html', context)

@login_required
def imprimir_pesagens(request):
    # Obtém os parâmetros do filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    lote_id = request.GET.get('lote_id')
    animal_id = request.GET.get('animal_id')
    
    # Query base otimizada - reduzido número de joins e adicionado índices
    pesagens = Pesagem.objects.select_related(
        'animal'
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
    
    # Limitar número de registros para evitar timeout
    pesagens = pesagens[:500]  # Limita a 500 registros mais recentes
    
    # Otimização: Buscar apenas os animais necessários
    animal_ids = set(pesagens.values_list('animal_id', flat=True))
    animais = {
        animal.id: animal for animal in Animal.objects.filter(
            id__in=animal_ids
        ).select_related('lote')
    }
    
    # Buscar rateios de uma vez só
    rateios = RateioCusto.objects.filter(
        animal_id__in=animal_ids
    ).select_related(
        'item_despesa',
        'item_despesa__categoria'
    )
    
    # Organizar rateios por animal
    rateios_por_animal = {}
    for rateio in rateios:
        if rateio.animal_id not in rateios_por_animal:
            rateios_por_animal[rateio.animal_id] = []
        rateios_por_animal[rateio.animal_id].append(rateio)
    
    # Converte para lista e adiciona pesos de entrada
    pesagens = list(pesagens)
    
    # Adiciona peso de entrada apenas se necessário e dentro do período
    for animal_id, animal in animais.items():
        if animal.peso_entrada and animal.data_entrada:
            # Verifica se a data de entrada está dentro do período filtrado
            if (not data_inicio or animal.data_entrada >= datetime.strptime(data_inicio, '%Y-%m-%d').date()) and \
               (not data_fim or animal.data_entrada <= datetime.strptime(data_fim, '%Y-%m-%d').date()):
                pesagens.append(Pesagem(
                    animal=animal,
                    peso=animal.peso_entrada,
                    data=animal.data_entrada,
                    usuario=request.user
                ))
    
    # Ordena todas as pesagens por data
    pesagens.sort(key=lambda x: x.data, reverse=True)
    
    dados_pesagens = []
    soma_ponderada_gmd = 0
    soma_dias = 0
    
    # Processa as pesagens
    for i, pesagem in enumerate(pesagens):
        animal = animais[pesagem.animal_id]
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
            'abaixo_media': False,
            'percentual_abaixo': 0,
            'dias_periodo': 0,
            'variacao_percentual': 0
        }
        
        # Otimização: Busca próxima pesagem mais eficientemente
        proximas_pesagens = [p for p in pesagens[i+1:i+2] if p.animal_id == animal.id]
        
        if proximas_pesagens:
            pesagem_anterior = proximas_pesagens[0]
            dias = (pesagem.data - pesagem_anterior.data).days
            peso_anterior = Decimal(str(pesagem_anterior.peso))
        elif animal.peso_entrada and animal.data_entrada:
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
                ganho_arroba = (kg_produzido / Decimal('15')) * Decimal('0.5')
                
                # Usa os rateios já carregados
                rateios_animal = rateios_por_animal.get(animal.id, [])
                custo_fixo = sum(
                    Decimal(str(rateio.valor)) 
                    for rateio in rateios_animal 
                    if rateio.item_despesa.categoria.tipo == 'fixo'
                )
                custo_variavel = sum(
                    Decimal(str(rateio.valor)) 
                    for rateio in rateios_animal 
                    if rateio.item_despesa.categoria.tipo == 'variavel'
                )
                
                # Adiciona custos das saídas de estoque
                custo_variavel += Decimal(str(animal.custo_variavel or '0'))
                
                custo_total = custo_fixo + custo_variavel
                
                if custo_total > 0 and ganho_arroba > 0:
                    dados['custo_arroba'] = round(float(custo_total / ganho_arroba), 2)
        
        dados_pesagens.append(dados)
    
    # Calcula a média ponderada do GMD
    media_gmd = round(soma_ponderada_gmd / soma_dias, 2) if soma_dias > 0 else None
    
    # Calcula a variação percentual para cada pesagem (limitado a 5 registros)
    for i, dados in enumerate(dados_pesagens):
        if dados['gmd'] and dados['gmd'] > 0:
            # Otimização: Limita a busca aos próximos 5 registros
            proximos_dados = [d for d in dados_pesagens[i+1:i+6] if d['animal'] == dados['animal'] and d['gmd'] and d['gmd'] > 0]
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
    
    # Prepara dados para os gráficos
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
    
    # Calcula médias por data para os gráficos
    datas = sorted(dados_por_data.keys())
    medias_peso = []
    medias_gmd = []
    medias_custo = []
    
    for data in datas:
        dados_data = dados_por_data[data]
        medias_peso.append(round(sum(dados_data['pesos']) / len(dados_data['pesos']), 2) if dados_data['pesos'] else 0)
        medias_gmd.append(round(sum(dados_data['gmd']) / len(dados_data['gmd']), 2) if dados_data['gmd'] else 0)
        medias_custo.append(round(sum(dados_data['custos']) / len(dados_data['custos']), 2) if dados_data['custos'] else 0)
    
    # Dados para os gráficos
    dados_graficos = {
        'datas': datas,
        'pesos': medias_peso,
        'gmd': medias_gmd,
        'custos': medias_custo
    }
    
    # Informações do cabeçalho
    cabecalho = {
        'empresa': 'FAZENDA MODELO LTDA',
        'cnpj': '12.345.678/0001-90',
        'endereco': 'Rodovia BR 101, Km 123'
    }
    
    # Obtém o lote selecionado se houver
    lote_selecionado = None
    if lote_id:
        lote_selecionado = Lote.objects.filter(id=lote_id).first()
    
    # Obtém o animal selecionado se houver
    animal_selecionado = None
    if animal_id:
        animal_selecionado = Animal.objects.filter(id=animal_id).first()
    
    context = {
        'dados_pesagens': dados_pesagens,
        'dados_graficos': dados_graficos,
        'media_gmd': media_gmd,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'lote_id': lote_id,
            'animal_id': animal_id
        },
        'lote_selecionado': lote_selecionado,
        'animal_selecionado': animal_selecionado,
        'cabecalho': cabecalho
    }
    
    return render(request, 'impressao/pesagens_print.html', context)

@login_required
def imprimir_confinamento(request):
    # Por enquanto retornamos apenas o template com dados fictícios
    # Posteriormente implementaremos a lógica real com os dados do banco
    context = {
        'cabecalho': {
            'empresa': 'Nome da Empresa'
        },
        'lote': 'PASTO-0003',
        'status': 'Em Andamento',
        'data_inicio': '01/01/2024',
        'total_animais': 100,
        'dias_confinamento': 90,
        'gmd': 1.33,
        'preco_transferencia_arroba': '300,00',
        'custo_pastagem': '15.000,00',
        'custo_nutricao': '45.000,00',
        'custo_total': '85.000,00',
        'lucro': '35.000,00',
        'roi': '41,18',
        'peso_medio_entrada': 360,
        'peso_medio_atual': 480,
        'ganho_peso_total': 120,
        'conversao_alimentar': 6.5,
        'arrobas_produzidas': 472
    }
    return render(request, 'impressao/confinamento_print.html', context)

@login_required
def despesas_print(request):
    # Query base
    despesas = Despesa.objects.filter(usuario=request.user)
    
    # Filtros
    contato = request.GET.get('contato')
    fazenda = request.GET.get('fazenda')
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    # Aplicar filtros
    if contato:
        despesas = despesas.filter(contato_id=contato)
    if status:
        despesas = despesas.filter(status=status)
    if data_inicio:
        despesas = despesas.filter(data_emissao__gte=data_inicio)
    if data_fim:
        despesas = despesas.filter(data_emissao__lte=data_fim)
    if fazenda:
        despesas = despesas.filter(itens__fazenda_destino_id=fazenda).distinct()
    
    # Ordenação
    despesas = despesas.order_by('-data_emissao')
    
    # Calcular valores totais
    valores_totais = {}
    total_geral = 0
    total_pago = 0
    
    for despesa in despesas:
        # Calcula o valor total desta despesa
        valor_itens = sum(item.valor_total for item in despesa.itens.all())
        valor_total = valor_itens + (despesa.multa_juros or 0) - (despesa.desconto or 0)
        
        # Armazena no dicionário
        valores_totais[despesa.id] = valor_total
        
        # Atualiza os totais
        total_geral += valor_total
        if despesa.status == 'PAGO':
            total_pago += valor_total
    
    total_pendente = total_geral - total_pago
    
    # Dados para os filtros
    filtros = {
        'contato': Contato.objects.filter(id=contato, usuario=request.user).first() if contato else None,
        'fazenda': Fazenda.objects.filter(id=fazenda, usuario=request.user).first() if fazenda else None,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }
    
    # Dados do cabeçalho
    cabecalho = {
        'empresa': request.user.first_name,
        'cnpj': request.user.profile.cnpj if hasattr(request.user, 'profile') else '',
        'endereco': request.user.profile.endereco if hasattr(request.user, 'profile') else '',
        'cidade': request.user.profile.cidade if hasattr(request.user, 'profile') else '',
        'estado': request.user.profile.estado if hasattr(request.user, 'profile') else ''
    }
    
    return render(request, 'impressao/despesas_print.html', {
        'despesas': despesas,
        'valores_totais': valores_totais,
        'filtros': filtros,
        'cabecalho': cabecalho,
        'total_geral': total_geral,
        'total_pago': total_pago,
        'total_pendente': total_pendente,
        'now': timezone.now()
    })

@login_required
def imprimir_compras(request):
    hoje = timezone.localdate()
    
    # Query base
    compras = Compra.objects.filter(usuario=request.user)
    
    # Filtros
    contato = request.GET.get('contato')
    fazenda = request.GET.get('fazenda')
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    # Aplicar filtros
    if contato:
        compras = compras.filter(vendedor_id=contato)
    if status:
        compras = compras.filter(status=status)
    if data_inicio:
        compras = compras.filter(data__gte=data_inicio)
    if data_fim:
        compras = compras.filter(data__lte=data_fim)
    if fazenda:
        compras = compras.filter(fazenda_destino_id=fazenda)
    
    # Ordenação
    compras = compras.order_by('-data')
    
    # Calcular totais por status
    totais_status = {
        'PAGO': {'valor': 0, 'cor': 'success', 'icone': 'fa-check-circle'},
        'PENDENTE': {'valor': 0, 'cor': 'warning', 'icone': 'fa-clock'},
        'VENCIDO': {'valor': 0, 'cor': 'danger', 'icone': 'fa-exclamation-circle'},
        'VENCE_HOJE': {'valor': 0, 'cor': 'info', 'icone': 'fa-calendar-check'},
    }

    # Calcular totais
    for compra in compras:
        valor_total = sum(item.valor_total for item in compra.animais.all())
        
        # Verificar status real da compra
        if compra.status == 'PAGO':
            totais_status['PAGO']['valor'] += valor_total
        elif compra.status == 'PENDENTE':
            if compra.data_vencimento == hoje:
                totais_status['VENCE_HOJE']['valor'] += valor_total
            elif compra.data_vencimento < hoje:
                totais_status['VENCIDO']['valor'] += valor_total
            else:
                totais_status['PENDENTE']['valor'] += valor_total

    # Formatar valores para exibição
    for status_info in totais_status.values():
        status_info['valor_formatado'] = f"R$ {status_info['valor']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

    # Contexto
    context = {
        'compras': compras,
        'totais_status': totais_status,
        'filtros': {
            'contato': contato,
            'fazenda': fazenda,
            'status': status,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        },
        'data_impressao': timezone.now(),
        'usuario': request.user
    }
    
    return render(request, 'impressao/compras_print.html', context)
