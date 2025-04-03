from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from .models import Animal, Pesagem, ManejoSanitario, MovimentacaoAnimal, RateioCusto, Lote
from .models_compras import CompraAnimal, Compra
from .models_vendas import VendaAnimal, Venda
from .models_abates import AbateAnimal
from .models_reproducao import ManejoReproducao, EstacaoMonta
from django.db.models import Sum, F, Q
from core.models import Despesa, Contato, Fazenda
from .views_relatorios import atualizar_dre_dados

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
        arrobas_final = peso_final / Decimal('30') if peso_atual else 0

    # Buscar históricos
    pesagens = Pesagem.objects.filter(animal=animal).order_by('-data')
    manejos = ManejoSanitario.objects.filter(animal=animal).order_by('-data')
    movimentacoes = MovimentacaoAnimal.objects.filter(animal=animal).order_by('-data_movimentacao')
    manejos_reprodutivos = ManejoReproducao.objects.filter(animal=animal).order_by('-data_concepcao')
    
    # Buscar filhos (bezerros) se o animal for fêmea
    filhos = []
    bezerros_organizados = []
    estacao_origem = None
    
    if animal.categoria_animal.sexo == 'F':
        # Buscar todos os filhos desta matriz
        filhos = Animal.objects.filter(mae=animal, usuario=request.user)
        
        # Organizar bezerros por estação de monta
        bezerros_por_estacao = {}
        
        for filho in filhos:
            # Buscar o manejo reprodutivo que originou este bezerro
            manejo_origem = ManejoReproducao.objects.filter(
                animal=animal,
                data_concepcao__lte=filho.data_nascimento,
                resultado='NASCIMENTO'
            ).order_by('-data_concepcao').first()
            
            estacao = None
            if manejo_origem and manejo_origem.estacao_monta:
                estacao = manejo_origem.estacao_monta
            
            # Adicionar à lista por estação
            if estacao not in bezerros_por_estacao:
                bezerros_por_estacao[estacao] = []
            
            bezerros_por_estacao[estacao].append(filho)
        
        # Converter para lista de dicionários para facilitar acesso no template
        bezerros_organizados = [
            {'estacao': estacao, 'bezerros': bezerros} 
            for estacao, bezerros in bezerros_por_estacao.items()
        ]
    
    # Se for um bezerro, buscar informação da estação de monta de origem
    elif animal.mae:
        # Buscar o manejo reprodutivo que originou este bezerro
        manejo_origem = ManejoReproducao.objects.filter(
            animal=animal.mae,
            data_concepcao__lte=animal.data_nascimento,
            resultado='NASCIMENTO'
        ).order_by('-data_concepcao').first()
        
        if manejo_origem and manejo_origem.estacao_monta:
            estacao_origem = manejo_origem.estacao_monta
    
    # Informações do cabeçalho
    # Obter a fazenda selecionada pelo usuário
    fazenda_atual = request.session.get('fazenda_atual')
    fazenda = None
    if fazenda_atual:
        fazenda = Fazenda.objects.filter(id=fazenda_atual).first()
    
    cabecalho = {
        'empresa': fazenda.nome if fazenda else request.user.first_name,
        'endereco': fazenda.endereco if fazenda and fazenda.endereco else "",
        'cidade': fazenda.cidade if fazenda else "",
        'estado': fazenda.estado if fazenda else "",
        'cnpj': fazenda.cnpj if fazenda and hasattr(fazenda, 'cnpj') else "",
        'logo_url': fazenda.logo_url if fazenda and fazenda.logo_url else None
    }
    
    # Preparar a URL do logo da fazenda, se existir
    fazenda_logo = fazenda.logo_url if fazenda and hasattr(fazenda, 'logo_url') and fazenda.logo_url else None
    
    # Obter data e hora local (UTC-3)
    from datetime import datetime
    import pytz
    
    # Definir o fuso horário do Brasil (UTC-3)
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    
    # Obter a data e hora atual no fuso horário do Brasil
    data_hora_local = datetime.now(tz_brasil)
    
    # Contexto
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
        'manejos_reprodutivos': manejos_reprodutivos,
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
        'bezerros_organizados': bezerros_organizados,
        'estacao_origem': estacao_origem,
        'cabecalho': cabecalho,
        'rodape': {
            'responsavel_tecnico': 'Dr. João Silva',
            'crmv': 'CRMV-MT 12345',
            'sistema': 'Sistema de Gestão Pecuária v1.0'
        },
        'data_hora_local': data_hora_local,
        'fazenda_logo': fazenda_logo,
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
    lote_selecionado = None
    if lote_id:
        lote_selecionado = Lote.objects.filter(id=lote_id).first()
        if lote_selecionado and lote_selecionado.fazenda:
            # Atualiza o cabeçalho com os dados da fazenda
            cabecalho = {
                'empresa': lote_selecionado.fazenda.nome,
                'endereco': f"{lote_selecionado.fazenda.cidade}/{lote_selecionado.fazenda.estado}"
            }
    
    # Obter o animal selecionado se houver
    animal_selecionado = None
    if animal_id:
        animal_selecionado = Animal.objects.filter(id=animal_id).first()
        if animal_selecionado and animal_selecionado.fazenda_atual:
            # Atualiza o cabeçalho com os dados da fazenda do animal
            cabecalho = {
                'empresa': animal_selecionado.fazenda_atual.nome,
                'endereco': f"{animal_selecionado.fazenda_atual.cidade}/{animal_selecionado.fazenda_atual.estado}"
            }
    
    # Verifica se há animais de diferentes fazendas no relatório
    fazendas_diferentes = False
    fazendas_ids = set()
    
    for dados in dados_pesagens:
        animal = Animal.objects.filter(brinco_visual=dados['animal']).first()
        if animal and animal.fazenda_atual:
            fazendas_ids.add(animal.fazenda_atual.id)
    
    fazendas_diferentes = len(fazendas_ids) > 1
    
    # Obter a logo da fazenda, se disponível
    fazenda_logo = None
    if lote_selecionado and lote_selecionado.fazenda and lote_selecionado.fazenda.logo_url:
        fazenda_logo = lote_selecionado.fazenda.logo_url
    elif animal_selecionado and animal_selecionado.fazenda_atual and animal_selecionado.fazenda_atual.logo_url:
        fazenda_logo = animal_selecionado.fazenda_atual.logo_url
    elif len(fazendas_ids) == 1:
        # Se todos os animais são da mesma fazenda, usa a logo dessa fazenda
        fazenda_id = list(fazendas_ids)[0]
        fazenda = Fazenda.objects.filter(id=fazenda_id).first()
        if fazenda and fazenda.logo_url:
            fazenda_logo = fazenda.logo_url
    
    # Contexto
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
        'cabecalho': {
            'empresa': fazenda.nome if fazenda else request.user.first_name,
            'endereco': f"{fazenda.cidade} - {fazenda.estado}" if fazenda else ""
        },
        'fazenda_logo': fazenda_logo,
        'fazendas_diferentes': fazendas_diferentes,
        'versao_sistema': '1.0.0',  # Versão do sistema
        'data_hora_local': datetime.now(pytz.timezone('America/Sao_Paulo')),
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
    # Obter a fazenda selecionada pelo usuário
    fazenda_atual = request.session.get('fazenda_atual')
    fazenda = None
    if fazenda_atual:
        fazenda = Fazenda.objects.filter(id=fazenda_atual).first()
    
    cabecalho = {
        'empresa': fazenda.nome if fazenda else request.user.first_name,
        'endereco': fazenda.endereco if fazenda and fazenda.endereco else "",
        'cidade': fazenda.cidade if fazenda else "",
        'estado': fazenda.estado if fazenda else "",
        'cnpj': fazenda.cnpj if fazenda and hasattr(fazenda, 'cnpj') else "",
        'logo_url': fazenda.logo_url if fazenda and fazenda.logo_url else None
    }
    
    # Preparar a URL do logo da fazenda, se existir
    fazenda_logo = fazenda.logo_url if fazenda and hasattr(fazenda, 'logo_url') and fazenda.logo_url else None
    
    # Obter data e hora local (UTC-3)
    from datetime import datetime
    import pytz
    
    # Definir o fuso horário do Brasil (UTC-3)
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    
    # Obter a data e hora atual no fuso horário do Brasil
    data_hora_local = datetime.now(tz_brasil)
    
    # Contexto
    context = {
        'despesas': despesas,
        'valores_totais': valores_totais,
        'filtros': filtros,
        'cabecalho': cabecalho,
        'total_geral': total_geral,
        'total_pago': total_pago,
        'total_pendente': total_pendente,
        'fazenda_logo': fazenda_logo,
        'versao_sistema': '1.0.0',
        'now': timezone.now(),
        'data_hora_local': data_hora_local,
    }
    
    return render(request, 'impressao/despesas_print.html', context)

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
        'PAGO': {'valor': Decimal('0.00'), 'cor': 'success', 'icone': 'fa-check-circle'},
        'PENDENTE': {'valor': Decimal('0.00'), 'cor': 'warning', 'icone': 'fa-clock'},
        'VENCIDO': {'valor': Decimal('0.00'), 'cor': 'danger', 'icone': 'fa-exclamation-circle'},
        'VENCE_HOJE': {'valor': Decimal('0.00'), 'cor': 'info', 'icone': 'fa-calendar-check'},
    }

    # Calcular totais
    for compra in compras:
        valor_total = compra.valor_total
        # Verificar status real da compra
        if compra.status == 'PAGO':
            totais_status['PAGO']['valor'] += valor_total
        elif compra.data_vencimento == hoje:
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
        'usuario': request.user,
    }
    
    return render(request, 'impressao/compras_print.html', context)

@login_required
def vendas_print(request):
    """View para impressão da lista de vendas"""
    vendas = Venda.objects.filter(usuario=request.user)
    
    # Aplicar os mesmos filtros da lista
    search_query = request.GET.get('search', '')
    status = request.GET.get('status')
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    if search_query:
        vendas = vendas.filter(
            Q(comprador__nome__icontains=search_query) |
            Q(animais__animal__brinco_visual__icontains=search_query)
        ).distinct()

    if status:
        vendas = vendas.filter(status=status)
    if data_inicial:
        vendas = vendas.filter(data__gte=data_inicial)
    if data_final:
        vendas = vendas.filter(data__lte=data_final)

    # Calcular totais
    totais_status = {
        'PAGO': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'PENDENTE': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'VENCE_HOJE': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'VENCIDO': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'}
    }

    hoje = timezone.now().date()

    for venda in vendas:
        valor_total = sum(Decimal(str(animal.valor_total)) for animal in venda.animais.all())
        
        if venda.status == 'PAGO':
            totais_status['PAGO']['valor'] += valor_total
        elif venda.data_vencimento == hoje:
            totais_status['VENCE_HOJE']['valor'] += valor_total
        elif venda.data_vencimento < hoje:
            totais_status['VENCIDO']['valor'] += valor_total
        else:
            totais_status['PENDENTE']['valor'] += valor_total

    # Formatar valores
    for status in totais_status:
        totais_status[status]['valor_formatado'] = f"R$ {totais_status[status]['valor']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

    # Contexto
    context = {
        'vendas': vendas,
        'totais_status': totais_status,
        'status_filter': status,
        'data_inicial': data_inicial,
        'data_final': data_final,
        'hoje': hoje
    }

    return render(request, 'core/vendas/print.html', context)

@login_required
def imprimir_vendas(request):
    # Obter os parâmetros do filtro
    comprador_id = request.GET.get('comprador')
    fazenda_id = request.GET.get('fazenda')
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Query base
    vendas = Venda.objects.filter(usuario=request.user)

    # Aplicar filtros
    if comprador_id:
        vendas = vendas.filter(contato_id=comprador_id)
    if fazenda_id:
        vendas = vendas.filter(fazenda_id=fazenda_id)
    if status:
        vendas = vendas.filter(status=status)
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        vendas = vendas.filter(data__gte=data_inicio)
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        vendas = vendas.filter(data__lte=data_fim)

    # Calcular totais por status
    totais_status = {
        'PAGO': {'valor': Decimal('0.00')},
        'PENDENTE': {'valor': Decimal('0.00')},
        'VENCE_HOJE': {'valor': Decimal('0.00')},
        'VENCIDO': {'valor': Decimal('0.00')}
    }

    hoje = timezone.now().date()
    
    for venda in vendas:
        if venda.status == 'PAGO':
            totais_status['PAGO']['valor'] += venda.valor_total
        elif venda.data_vencimento == hoje:
            totais_status['VENCE_HOJE']['valor'] += venda.valor_total
        elif venda.data_vencimento < hoje:
            totais_status['VENCIDO']['valor'] += venda.valor_total
        else:
            totais_status['PENDENTE']['valor'] += venda.valor_total

    # Formatar os valores
    for status in totais_status:
        totais_status[status]['valor_formatado'] = f"R$ {totais_status[status]['valor']:,.2f}"

    # Preparar filtros para exibição
    filtros = {
        'contato': Contato.objects.filter(id=comprador_id).first() if comprador_id else None,
        'fazenda': Fazenda.objects.filter(id=fazenda_id).first() if fazenda_id else None,
        'status': dict(Venda.STATUS_CHOICES).get(status) if status else None,
        'data_inicio': data_inicio if data_inicio else None,
        'data_fim': data_fim if data_fim else None,
    }

    # Obter data e hora local (UTC-3)
    from datetime import datetime
    import pytz
    
    # Definir o fuso horário do Brasil (UTC-3)
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    
    # Obter a data e hora atual no fuso horário do Brasil
    data_hora_local = datetime.now(tz_brasil)
    
    # Contexto
    context = {
        'vendas': vendas,
        'totais_status': totais_status,
        'filtros': filtros,
        'data_impressao': timezone.now(),
        'usuario': request.user,
        'data_hora_local': data_hora_local,
    }

    return render(request, 'impressao/vendas_print.html', context)

@login_required
def imprimir_dre(request):
    """
    View para impressão do relatório DRE
    """
    # Obter dados da fazenda do usuário
    fazenda_id = request.GET.get('fazenda_id')
    fazenda = None
    fazenda_logo = None
    
    # Filtros
    data_inicial_str = request.GET.get('data_inicial')
    data_final_str = request.GET.get('data_final')
    
    # Dados do relatório
    dados_dre = None
    if data_inicial_str and data_final_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            dados_dre = atualizar_dre_dados(request.user, data_inicial, data_final, fazenda_id)
            print(f"Dados DRE obtidos: {dados_dre}")
        except ValueError as e:
            print(f"Erro ao processar datas: {e}")
        except Exception as e:
            print(f"Erro ao obter dados do DRE: {e}")
    
    # Obter dados da fazenda para o cabeçalho
    if fazenda_id:
        try:
            fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
            fazenda_logo = fazenda.logo_url
        except Fazenda.DoesNotExist:
            pass
    
    # Se não tiver fazenda específica, pegar a primeira do usuário
    if not fazenda:
        fazenda = Fazenda.objects.filter(usuario=request.user).first()
        if fazenda:
            fazenda_logo = fazenda.logo_url
    
    # Montar dados do cabeçalho
    # Obter a fazenda selecionada pelo usuário
    fazenda_atual = request.session.get('fazenda_atual')
    fazenda = None
    if fazenda_atual:
        fazenda = Fazenda.objects.filter(id=fazenda_atual).first()
    
    cabecalho = {
        'empresa': fazenda.nome if fazenda else request.user.first_name,
        'endereco': fazenda.endereco if fazenda and fazenda.endereco else "",
        'cidade': fazenda.cidade if fazenda else "",
        'estado': fazenda.estado if fazenda else "",
        'cnpj': fazenda.cnpj if fazenda and hasattr(fazenda, 'cnpj') else "",
        'logo_url': fazenda.logo_url if fazenda and fazenda.logo_url else None
    }
    
    # Dados dos filtros para exibição
    filtros = {
        'data_inicial': data_inicial_str,
        'data_final': data_final_str,
        'fazenda': fazenda.nome if fazenda else None,
    }
    
    # Versão do sistema
    from django.conf import settings
    versao_sistema = getattr(settings, 'VERSION', '1.0.0')
    
    # Contexto
    context = {
        'cabecalho': cabecalho,
        'fazenda_logo': fazenda_logo,
        'dados_dre': dados_dre,
        'filtros': filtros,
        'versao_sistema': versao_sistema,
    }
    
    return render(request, 'impressao/dre_print.html', context)

@login_required
def imprimir_fluxo_caixa(request):
    """
    View para impressão do relatório de Fluxo de Caixa
    """
    # Obter os parâmetros do filtro
    mes_ano_inicial = request.GET.get('mes_ano_inicial')
    fazenda_id = request.GET.get('fazenda')
    
    # Variáveis para armazenar os dados
    dados_fluxo = None
    fazenda = None
    fazenda_logo = None
    data_inicial = None
    data_final = None
    mensagem_erro = None
    
    # Processar os dados se os filtros estiverem presentes
    if mes_ano_inicial:
        try:
            # Converter o mês/ano para data inicial (primeiro dia do mês)
            # O formato do campo month HTML é YYYY-MM
            print(f"Valor do campo mes_ano_inicial: {mes_ano_inicial}")
            
            if '-' in mes_ano_inicial:
                ano, mes = mes_ano_inicial.split('-')
                print(f"Formato YYYY-MM detectado: ano={ano}, mes={mes}")
            else:
                mes, ano = mes_ano_inicial.split('/')
                print(f"Formato MM/YYYY detectado: mes={mes}, ano={ano}")
            
            # Converter para inteiros e verificar se estão no intervalo válido
            mes = int(mes)
            ano = int(ano)
            print(f"Após conversão: ano={ano}, mes={mes}")
            
            if mes < 1 or mes > 12:
                raise ValueError(f"Mês inválido: {mes}. Deve estar entre 1 e 12.")
                
            data_inicial = datetime(ano, mes, 1).date()
            print(f"Data inicial criada: {data_inicial}")
            
            # Calcular a data final (12 meses depois)
            if mes == 12:
                data_final = datetime(ano + 1, 12, 31).date()
            else:
                # Calcular mês e ano final (12 meses depois)
                ano_final = ano + 1
                mes_final = mes - 1
                if mes_final == 0:
                    mes_final = 12
                    ano_final = ano
                
                print(f"Calculando data final: ano_final={ano_final}, mes_final={mes_final}")
                
                # Último dia do mês
                from calendar import monthrange
                ultimo_dia = monthrange(ano_final, mes_final)[1]
                data_final = datetime(ano_final, mes_final, ultimo_dia).date()
            
            # Implementação temporária para evitar o erro
            dados_fluxo = {
                'entradas': [],
                'saidas': [],
                'saldo_inicial': 0,
                'total_entradas': 0,
                'total_saidas': 0,
                'saldo_final': 0
            }
            
            # Adicionar as datas calculadas ao contexto para uso no template
            dados_fluxo['data_inicial'] = data_inicial
            dados_fluxo['data_final'] = data_final
            
            # Obter a fazenda se o ID estiver presente
            if fazenda_id:
                fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
                fazenda_logo = fazenda.logo_url
        except ValueError as e:
            print(f"Erro ao processar datas: {e}")
            mensagem_erro = f"Erro ao processar datas: {e}"
        except Exception as e:
            print(f"Erro ao processar dados do fluxo de caixa: {e}")
            mensagem_erro = f"Erro ao processar dados: {e}"
    
    # Montar dados do cabeçalho
    # Obter a fazenda selecionada pelo usuário
    fazenda_atual = request.session.get('fazenda_atual')
    fazenda = None
    if fazenda_atual:
        fazenda = Fazenda.objects.filter(id=fazenda_atual).first()
    
    cabecalho = {
        'empresa': fazenda.nome if fazenda else request.user.first_name,
        'endereco': fazenda.endereco if fazenda and fazenda.endereco else "",
        'cidade': fazenda.cidade if fazenda else "",
        'estado': fazenda.estado if fazenda else "",
        'cnpj': fazenda.cnpj if fazenda and hasattr(fazenda, 'cnpj') else "",
        'logo_url': fazenda.logo_url if fazenda and fazenda.logo_url else None
    }
    
    # Dados dos filtros para exibição
    filtros = {
        'data_inicial': data_inicial,
        'data_final': data_final,
        'fazenda': fazenda.nome if fazenda else None,
    }
    
    # Versão do sistema
    from django.conf import settings
    versao_sistema = getattr(settings, 'VERSION', '1.0.0')
    
    # Contexto
    context = {
        'cabecalho': cabecalho,
        'fazenda_logo': fazenda_logo,
        'dados_fluxo': dados_fluxo,
        'filtros': filtros,
        'versao_sistema': versao_sistema,
        'fazenda_selecionada': fazenda,
        'mensagem_erro': mensagem_erro,
    }
    
    return render(request, 'impressao/fluxo_caixa_print.html', context)
