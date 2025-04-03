from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import random
import logging
from django.contrib import messages

# Configurar o logger
logger = logging.getLogger(__name__)

# Importar apenas os modelos que realmente existem no projeto
from .models import Fazenda, Animal, Pesagem, Lote, Pasto, Despesa, ContaBancaria, ExtratoBancario, MovimentacaoNaoOperacional
from .models_vendas import Venda
from .models_compras import Compra
from .models_abates import Abate

@login_required
def dashboard_simples(request):
    """
    Dashboard extremamente simples que garante funcionamento
    """
    try:
        # Obtém a fazenda atual do usuário
        fazenda_id = request.session.get('fazenda_id')
        
        # Filtrar animais pela fazenda
        animais = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='ATIVO')
        
        # Obter lotes e pastos
        lotes = Lote.objects.filter(fazenda_id=fazenda_id)
        
        # Obter pastos
        pastos = Pasto.objects.filter(fazenda_id=fazenda_id)
        
        # Contagem de animais
        total_animais = Animal.objects.filter(fazenda_atual_id=fazenda_id).count()
        animais_ativos = animais.count()
        animais_vendidos = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='VENDIDO').count()
        animais_abatidos = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='ABATIDO').count()
        animais_mortos = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='MORTO').count()
        
        # Distribuição de animais por lote
        distribuicao_lotes = []
        cores_lotes = gerar_cores(len(lotes))
        
        for i, lote in enumerate(lotes):
            # Contar animais por lote
            quantidade = Animal.objects.filter(fazenda_atual_id=fazenda_id, lote_id=lote.id, situacao='ATIVO').count()
            
            # Nome do lote (usar ID se não tiver nome)
            nome_lote = getattr(lote, 'nome', None) or f"Lote {lote.id_lote}"
            
            # Adicionar à lista de distribuição
            if quantidade > 0:
                distribuicao_lotes.append({
                    'id': lote.id_lote,
                    'nome': nome_lote,
                    'quantidade': quantidade,
                    'cor': cores_lotes[i % len(cores_lotes)]
                })
        
        # Distribuição de animais por pasto
        distribuicao_pastos = []
        cores_pastos = gerar_cores(len(pastos))
        
        for i, pasto in enumerate(pastos):
            # Contar animais por pasto
            quantidade = Animal.objects.filter(fazenda_atual_id=fazenda_id, pasto_atual_id=pasto.id, situacao='ATIVO').count()
            
            # Nome do pasto (usar ID se não tiver nome)
            nome_pasto = getattr(pasto, 'nome', None) or f"Pasto {pasto.id_pasto}"
            
            # Adicionar à lista de distribuição (incluir mesmo se não tiver animais)
            distribuicao_pastos.append({
                'id': pasto.id_pasto,
                'nome': nome_pasto,
                'quantidade': quantidade,
                'cor': cores_pastos[i % len(cores_pastos)],
                'area': getattr(pasto, 'area', 0) or 0
            })
        
        # Dados para o mapa de pastos
        dados_pastos = []
        for pasto in pastos:
            # Verificar se o pasto tem coordenadas
            coordenadas = getattr(pasto, 'coordenadas', None)
            if coordenadas:
                # Adicionar dados do pasto
                dados_pastos.append({
                    'id_pasto': pasto.id_pasto,
                    'nome': getattr(pasto, 'nome', None) or f"Pasto {pasto.id_pasto}",
                    'fazenda_id': fazenda_id,
                    'fazenda_nome': Fazenda.objects.get(id_fazenda=fazenda_id).nome,
                    'coordenadas': coordenadas,
                    'area': getattr(pasto, 'area', 0) or 0,
                    'capacidade_ua': getattr(pasto, 'capacidade_ua', 0) or 0,
                    'variedade_capim': getattr(pasto, 'variedade_capim', '') or ''
                })
        
        # Dados de pesagem
        ultima_pesagem = None
        peso_medio = 0
        
        try:
            # Obter a data da última pesagem
            ultima_pesagem = Pesagem.objects.filter(
                animal__fazenda_atual_id=fazenda_id
            ).order_by('-data').first()
            
            if ultima_pesagem:
                # Calcular o peso médio dos animais ativos
                peso_medio = Pesagem.objects.filter(
                    animal__fazenda_atual_id=fazenda_id,
                    animal__situacao='ATIVO',
                    data=ultima_pesagem.data
                ).aggregate(Avg('peso'))['peso__avg'] or 0
        except Exception as e:
            logger.error(f"Erro ao obter dados de pesagem: {e}")
            ultima_pesagem = None
            peso_medio = 0
        
        # Dados financeiros
        try:
            # Despesas pendentes
            despesas_pendentes = Despesa.objects.filter(
                fazenda_id=fazenda_id,
                situacao='PENDENTE'
            ).aggregate(total=Sum('valor'))['total'] or 0
            
            # Despesas pagas
            despesas_pagas = Despesa.objects.filter(
                fazenda_id=fazenda_id,
                situacao='PAGO'
            ).aggregate(total=Sum('valor'))['total'] or 0
            
            # Receitas de abates
            receitas_abates = Abate.objects.filter(
                animal__fazenda_atual_id=fazenda_id,
                data__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('valor_total'))['total'] or 0
            
        except Exception as e:
            logger.error(f"Erro ao obter dados financeiros: {e}")
            despesas_pendentes = 0
            despesas_pagas = 0
            receitas_abates = 0
        
        # Indicadores globais
        indicadores_globais = {
            'gmd': calcular_gmd(fazenda_id),
            'producao_hectare': calcular_producao_hectare(fazenda_id),
            'taxa_lotacao': calcular_taxa_lotacao(fazenda_id),
            'eficiencia_alimentar': calcular_eficiencia_alimentar(fazenda_id)
        }
        
        # Renderizar o template com os dados
        return render(request, 'dashboard_simples.html', {
            'total_animais': total_animais,
            'animais_ativos': animais_ativos,
            'animais_vendidos': animais_vendidos,
            'animais_abatidos': animais_abatidos,
            'animais_mortos': animais_mortos,
            'distribuicao_lotes': json.dumps(distribuicao_lotes),
            'distribuicao_pastos': json.dumps(distribuicao_pastos),
            'dados_pastos': json.dumps(dados_pastos),
            'ultima_pesagem': ultima_pesagem,
            'peso_medio': peso_medio,
            'despesas_pendentes': despesas_pendentes,
            'despesas_pagas': despesas_pagas,
            'receitas_abates': receitas_abates,
            'indicadores_globais': indicadores_globais
        })
    
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        messages.error(request, f"Erro ao carregar o dashboard: {e}")
        return redirect('dashboard')

def gerar_cores(quantidade):
    """
    Gera uma lista de cores para uso nos gráficos
    """
    cores_base = [
        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
        '#6f42c1', '#fd7e14', '#20c9a6', '#5a5c69', '#858796'
    ]
    
    # Se a quantidade for menor que o número de cores base, retorna apenas as cores necessárias
    if quantidade <= len(cores_base):
        return cores_base[:quantidade]
    
    # Caso contrário, gera cores aleatórias para complementar
    cores = cores_base.copy()
    for _ in range(quantidade - len(cores_base)):
        # Gera uma cor aleatória em formato hexadecimal
        cor = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        cores.append(cor)
    
    return cores

def calcular_gmd(fazenda_id):
    """
    Calcula o Ganho Médio Diário (GMD) dos animais da fazenda
    """
    try:
        # Obter os animais ativos da fazenda
        animais = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='ATIVO')
        
        gmd_total = 0
        animais_com_gmd = 0
        
        for animal in animais:
            # Obter as duas últimas pesagens do animal
            pesagens = Pesagem.objects.filter(animal=animal).order_by('-data')[:2]
            
            if len(pesagens) >= 2:
                # Calcular o GMD
                peso_atual = pesagens[0].peso
                peso_anterior = pesagens[1].peso
                dias = (pesagens[0].data - pesagens[1].data).days
                
                if dias > 0:
                    gmd = (peso_atual - peso_anterior) / dias
                    gmd_total += gmd
                    animais_com_gmd += 1
        
        # Calcular a média do GMD
        if animais_com_gmd > 0:
            return gmd_total / animais_com_gmd
        else:
            return 0
    
    except Exception as e:
        logger.error(f"Erro ao calcular GMD: {e}")
        return 0

def calcular_producao_hectare(fazenda_id):
    """
    Calcula a produção por hectare da fazenda
    """
    try:
        # Obter a área total dos pastos da fazenda
        area_total = Pasto.objects.filter(fazenda_id=fazenda_id).aggregate(total=Sum('area'))['total'] or 0
        
        # Se não houver área, retornar 0
        if area_total <= 0:
            return 0
        
        # Obter os animais ativos da fazenda
        animais = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='ATIVO')
        
        # Calcular o peso total dos animais
        peso_total = 0
        for animal in animais:
            # Obter a última pesagem do animal
            ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
            
            if ultima_pesagem:
                peso_total += ultima_pesagem.peso
        
        # Calcular a produção por hectare
        return peso_total / area_total
    
    except Exception as e:
        logger.error(f"Erro ao calcular produção por hectare: {e}")
        return 0

def calcular_taxa_lotacao(fazenda_id):
    """
    Calcula a taxa de lotação da fazenda (UA/ha)
    """
    try:
        # Obter a área total dos pastos da fazenda
        area_total = Pasto.objects.filter(fazenda_id=fazenda_id).aggregate(total=Sum('area'))['total'] or 0
        
        # Se não houver área, retornar 0
        if area_total <= 0:
            return 0
        
        # Calcular o total de UA (Unidade Animal)
        total_ua = 0
        animais = Animal.objects.filter(fazenda_atual_id=fazenda_id, situacao='ATIVO')
        
        for animal in animais:
            # Obter a última pesagem do animal
            ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
            
            if ultima_pesagem:
                # Converter peso para UA (1 UA = 450 kg)
                ua = ultima_pesagem.peso / 450
                total_ua += ua
        
        # Calcular a taxa de lotação
        return total_ua / area_total
    
    except Exception as e:
        logger.error(f"Erro ao calcular taxa de lotação: {e}")
        return 0

def calcular_eficiencia_alimentar(fazenda_id):
    """
    Calcula a eficiência alimentar dos animais da fazenda
    """
    # Implementação simplificada - em um sistema real, seria necessário
    # ter dados de consumo de alimentos para calcular a eficiência alimentar
    return 0

@login_required
def dashboard_dados_simples(request):
    """
    API simplificada para fornecer dados para o dashboard
    """
    try:
        # Parâmetros da requisição
        fazenda_id = request.GET.get('fazenda')
        periodo_dias = request.GET.get('periodo', '30')  # Padrão: 30 dias
        
        # Converter período para inteiro
        try:
            periodo_dias = int(periodo_dias)
        except (ValueError, TypeError):
            periodo_dias = 30  # Valor padrão se houver erro
        
        # Calcular data de início com base no período
        hoje = date.today()
        if periodo_dias > 0:
            data_inicio = hoje - timedelta(days=periodo_dias)
        else:
            # Se período for 0, considerar todo o histórico
            data_inicio = date(2000, 1, 1)  # Data bem antiga para pegar todo o histórico
        
        # Filtro base
        filtro_base = {'usuario': request.user}  # Adicionar filtro por usuário
        filtro_fazenda = {}
        
        # Log para depuração
        print(f"Aplicando filtros - Fazenda ID: {fazenda_id}, Período: {periodo_dias} dias")
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_base['fazenda_atual_id'] = fazenda_id
            filtro_fazenda['id'] = fazenda_id
            print(f"Filtro de fazenda aplicado: {fazenda_id}")
        else:
            print("Nenhum filtro de fazenda aplicado (todas as fazendas)")
        
        # Contagem de animais por situação
        animais_ativos = Animal.objects.filter(situacao='ATIVO', **filtro_base).count()
        animais_vendidos = Animal.objects.filter(situacao='VENDIDO', **filtro_base).count()
        animais_abatidos = Animal.objects.filter(situacao='ABATIDO', **filtro_base).count()
        animais_mortos = Animal.objects.filter(situacao='MORTO', **filtro_base).count()
        
        # Dados adicionais
        # Contagem por lotes (top 5)
        contagem_por_lote = []
        
        # Buscar lotes do usuário
        lotes_query = Lote.objects.filter(usuario=request.user)
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            lotes_query = lotes_query.filter(fazenda_id=fazenda_id)
            
        # Ordenar e limitar a 5 lotes
        lotes = lotes_query.order_by('id_lote')[:5]
        
        for lote in lotes:
            filtro_lote = {'situacao': 'ATIVO', 'lote': lote}
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                filtro_lote['fazenda_atual_id'] = fazenda_id
                
            count = Animal.objects.filter(**filtro_lote).count()
            if count > 0:
                contagem_por_lote.append({
                    'nome': lote.id_lote,  # Usar o ID do lote
                    'quantidade': count
                })
        
        # Contagem por pastos (top 5)
        contagem_por_pasto = []
        
        # Buscar pastos da fazenda (Pasto não tem campo usuario)
        pastos_query = Pasto.objects.all()
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            pastos_query = pastos_query.filter(fazenda_id=fazenda_id)
            
        pastos = pastos_query.order_by('id_pasto')[:5]  # Limitar a 5 pastos
        
        for pasto in pastos:
            filtro_pasto = {'situacao': 'ATIVO', 'pasto_atual': pasto}
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                filtro_pasto['fazenda_atual_id'] = fazenda_id
                
            count = Animal.objects.filter(**filtro_pasto).count()
            if count > 0:
                contagem_por_pasto.append({
                    'nome': pasto.id_pasto,  # Usar id_pasto como nome
                    'quantidade': count
                })
        
        # Dados de pesagem (média, última data)
        dados_pesagem = {
            'ultima_data': None,
            'peso_medio': None,
            'total_pesado': 0
        }
        
        # Obter a data da última pesagem
        ultima_pesagem = Pesagem.objects.filter(animal__usuario=request.user).order_by('-data').first()
        if ultima_pesagem:
            dados_pesagem['ultima_data'] = ultima_pesagem.data.strftime('%d/%m/%Y')
            
            # Calcular peso médio das pesagens mais recentes de cada animal
            animais_ids = Animal.objects.filter(situacao='ATIVO', **filtro_base).values_list('id', flat=True)
            
            # Subconsulta para obter a pesagem mais recente de cada animal
            ultimas_pesagens = {}
            for animal_id in animais_ids:
                pesagem = Pesagem.objects.filter(animal_id=animal_id).order_by('-data').first()
                if pesagem:
                    ultimas_pesagens[animal_id] = pesagem
            
            # Calcular média
            if ultimas_pesagens:
                peso_total = sum(p.peso for p in ultimas_pesagens.values())
                dados_pesagem['peso_medio'] = peso_total / len(ultimas_pesagens)
                dados_pesagem['total_pesado'] = len(ultimas_pesagens)
        
        # Dados financeiros
        dados_financeiros = obter_dados_financeiros(request.user, fazenda_id)
        
        # Dados dos pastos para o mapa
        pastos_json = []
        cores_fazendas = {}
        
        # Cores pré-definidas para as fazendas
        cores = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', 
                '#800000', '#008000', '#000080', '#808000', '#800080', '#008080']
        
        # Obter todas as fazendas do usuário para as cores
        fazendas = Fazenda.objects.filter(usuario=request.user)
        for idx, fazenda in enumerate(fazendas):
            cores_fazendas[fazenda.id] = cores[idx % len(cores)]
        
        # Filtrar pastos conforme necessário
        pastos_mapa = Pasto.objects.filter(fazenda__usuario=request.user)
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            pastos_mapa = pastos_mapa.filter(fazenda_id=fazenda_id)
        
        for pasto in pastos_mapa:
            pastos_json.append({
                'id': pasto.id,
                'id_pasto': pasto.id_pasto,
                'nome': pasto.nome,
                'fazenda_nome': pasto.fazenda.nome,
                'fazenda_id': pasto.fazenda.id,
                'area': float(pasto.area),
                'capacidade_ua': float(pasto.capacidade_ua),
                'coordenadas': pasto.coordenadas,
                'cor': cores_fazendas[pasto.fazenda.id]
            })
        
        # Indicadores globais
        indicadores_globais = obter_indicadores_globais(request.user, fazenda_id)
        
        # Preparar resposta
        response_data = {
            'success': True,
            'timestamp': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
            'contagem_animais': {
                'ativos': animais_ativos,
                'vendidos': animais_vendidos,
                'abatidos': animais_abatidos,
                'mortos': animais_mortos,
            },
            'contagem_por_lote': contagem_por_lote,
            'contagem_por_pasto': contagem_por_pasto,
            'dados_pesagem': dados_pesagem,
            'dados_financeiros': dados_financeiros,
            'pastos_json': pastos_json,
            'indicadores_globais': indicadores_globais
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Erro no dashboard: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def obter_dados_financeiros(usuario, fazenda_id=None, data_inicio=None):
    """
    Obtém dados financeiros para o dashboard
    """
    try:
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
        
        total_receitas_pendentes = receitas.aggregate(total=Sum('valor'))['total'] or 0
        
        return {
            'saldo_total': saldo_total,
            'despesas_pendentes': total_despesas_pendentes,
            'receitas_pendentes': total_receitas_pendentes,
            'inicio_mes': inicio_mes_atual,
            'fim_mes': fim_mes_atual
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados financeiros: {e}")
        return {
            'saldo_total': 0,
            'despesas_pendentes': 0,
            'receitas_pendentes': 0
        }

def obter_entradas_saidas_12_meses(usuario, fazenda_id=None):
    """
    Obtém dados de entradas e saídas dos últimos 12 meses
    """
    try:
        # Definir período
        hoje = date.today()
        meses = []
        entradas = []
        saidas = []
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        filtro_fazenda = {}
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_fazenda = {'fazenda_atual_id': fazenda_id}
        
        # Obter dados para os últimos 12 meses
        for i in range(11, -1, -1):
            # Calcular início e fim do mês
            data_ref = hoje - timedelta(days=30 * i)
            inicio_mes = date(data_ref.year, data_ref.month, 1)
            fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Adicionar nome do mês à lista
            nome_mes = inicio_mes.strftime('%b/%y')
            meses.append(nome_mes)
            
            # Calcular entradas do mês
            entrada_mes = 0
            
            # Vendas
            vendas = Venda.objects.filter(
                data__gte=inicio_mes,
                data__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                vendas = vendas.filter(**filtro_fazenda)
            
            for venda in vendas:
                entrada_mes += venda.valor_recebido or 0
            
            # Abates
            abates = Abate.objects.filter(
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                abates = abates.filter(**filtro_fazenda)
            
            for abate in abates:
                entrada_mes += abate.valor_recebido or 0
            
            # Outras entradas
            outras_entradas = MovimentacaoNaoOperacional.objects.filter(
                tipo='entrada',
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                outras_entradas = outras_entradas.filter(**filtro_fazenda)
            
            for entrada in outras_entradas:
                entrada_mes += entrada.valor or 0
            
            # Adicionar total de entradas à lista
            entradas.append(float(entrada_mes))
            
            # Calcular saídas do mês
            saida_mes = 0
            
            # Despesas
            despesas = Despesa.objects.filter(
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                despesas = despesas.filter(**filtro_fazenda)
            
            for despesa in despesas:
                saida_mes += despesa.valor_final() or 0
            
            # Compras de animais - Usar data da compra em vez de data de pagamento
            # para garantir que todas as compras sejam consideradas
            compras = Compra.objects.filter(
                data__gte=inicio_mes,
                data__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                compras = compras.filter(**filtro_fazenda)
            
            for compra in compras:
                saida_mes += compra.valor_total or 0  # Usar valor_total em vez de valor
            
            # Outras saídas
            outras_saidas = MovimentacaoNaoOperacional.objects.filter(
                tipo='saida',
                data_pagamento__gte=inicio_mes,
                data_pagamento__lte=fim_mes,
                **filtro_usuario
            )
            
            if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
                outras_saidas = outras_saidas.filter(**filtro_fazenda)
            
            for saida in outras_saidas:
                saida_mes += saida.valor or 0
            
            # Adicionar total de saídas à lista
            saidas.append(float(saida_mes))
        
        return {
            'meses': meses,
            'entradas': entradas,
            'saidas': saidas
        }
    except Exception as e:
        print(f"Erro ao obter entradas e saídas dos últimos 12 meses: {e}")
        return {
            'meses': [],
            'entradas': [],
            'saidas': [],
            'erro': str(e)
        }

def obter_categorias_custo(usuario, fazenda_id=None):
    """
    Obtém dados de categorias de custo para o dashboard
    """
    try:
        # Definir período (últimos 12 meses)
        hoje = date.today()
        inicio_periodo = hoje - timedelta(days=365)
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        filtro_fazenda = {}
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_fazenda = {'fazenda_atual_id': fazenda_id}
        
        # Obter despesas agrupadas por categoria
        despesas = Despesa.objects.filter(
            data_pagamento__gte=inicio_periodo,
            data_pagamento__lte=hoje,
            **filtro_usuario
        )
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            despesas = despesas.filter(**filtro_fazenda)
        
        # Agrupar por categoria
        categorias = {}
        
        for despesa in despesas:
            # Obter o nome da categoria diretamente da despesa
            # Se a despesa não tiver categoria, usar 'Sem categoria'
            try:
                categoria = despesa.categoria.nome if despesa.categoria else 'Sem categoria'
            except:
                categoria = 'Sem categoria'
            
            if categoria not in categorias:
                categorias[categoria] = 0
            
            categorias[categoria] += despesa.valor_final() or 0
        
        # Converter para lista de dicionários
        resultado = []
        
        for categoria, valor in categorias.items():
            resultado.append({
                'nome': categoria,
                'valor': float(valor)
            })
        
        # Ordenar por valor (decrescente)
        resultado.sort(key=lambda x: x['valor'], reverse=True)
        
        # Limitar a 5 categorias principais
        if len(resultado) > 5:
            # Somar as demais categorias
            outras_valor = sum(item['valor'] for item in resultado[5:])
            
            # Adicionar categoria "Outras"
            if outras_valor > 0:
                resultado = resultado[:5]
                resultado.append({
                    'nome': 'Outras',
                    'valor': outras_valor
                })
        
        return resultado
    except Exception as e:
        print(f"Erro ao obter categorias de custo: {e}")
        return []

def obter_contas_a_pagar(usuario, fazenda_id=None):
    """
    Obtém contas a pagar para o dashboard
    """
    try:
        hoje = date.today()
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        filtro_fazenda = {}
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_fazenda = {'fazenda_atual_id': fazenda_id}
        
        # Obter despesas não pagas
        despesas = Despesa.objects.filter(
            situacao='PENDENTE',
            **filtro_usuario
        )
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            despesas = despesas.filter(**filtro_fazenda)
        
        # Criar lista de contas a pagar
        contas = []
        
        for despesa in despesas:
            # Determinar status
            status = 'futura'
            
            if despesa.data_vencimento < hoje:
                status = 'vencida'
            elif (despesa.data_vencimento - hoje).days <= 7:
                status = 'proxima'
            
            contas.append({
                'descricao': despesa.descricao,
                'valor': float(despesa.valor),
                'data_vencimento': despesa.data_vencimento.strftime('%d/%m/%Y'),
                'status': status
            })
        
        # Ordenar por data de vencimento
        contas.sort(key=lambda x: datetime.strptime(x['data_vencimento'], '%d/%m/%Y'))
        
        # Limitar a 10 contas
        return contas[:10]
    except Exception as e:
        print(f"Erro ao obter contas a pagar: {e}")
        return []

def obter_indicadores_globais(usuario, fazenda_id=None):
    """
    Calcula indicadores globais como GMD (Ganho Médio Diário) e produção por hectare
    """
    try:
        # Definir período
        hoje = date.today()
        data_inicial_gmd = hoje - timedelta(days=30)  # Últimos 30 dias para GMD
        data_inicial_prod = hoje - timedelta(days=365)  # Últimos 12 meses para produção/hectare
        
        # Filtros base
        filtro_usuario = {'usuario': usuario}
        filtro_fazenda = {}
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_fazenda = {'fazenda_atual_id': fazenda_id}
        
        # Calcular GMD (Ganho Médio Diário)
        # Obter pesagens no período
        pesagens = Pesagem.objects.filter(
            data__gte=data_inicial_gmd,
            data__lte=hoje,
            animal__usuario=usuario
        )
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            pesagens = pesagens.filter(animal__fazenda_atual_id=fazenda_id)
        
        # Agrupar pesagens por animal
        animais_pesados = {}
        for pesagem in pesagens:
            animal_id = pesagem.animal.id
            if animal_id not in animais_pesados:
                animais_pesados[animal_id] = []
            
            animais_pesados[animal_id].append({
                'data': pesagem.data,
                'peso': pesagem.peso
            })
        
        # Calcular GMD para cada animal
        gmd_total = 0
        animais_com_gmd = 0
        
        for animal_id, pesagens_animal in animais_pesados.items():
            # Ordenar pesagens por data
            pesagens_animal.sort(key=lambda x: x['data'])
            
            # Se o animal tem pelo menos duas pesagens no período
            if len(pesagens_animal) >= 2:
                primeira_pesagem = pesagens_animal[0]
                ultima_pesagem = pesagens_animal[-1]
                
                dias = (ultima_pesagem['data'] - primeira_pesagem['data']).days
                
                # Evitar divisão por zero
                if dias > 0:
                    ganho = ultima_pesagem['peso'] - primeira_pesagem['peso']
                    gmd_animal = ganho / dias
                    
                    gmd_total += gmd_animal
                    animais_com_gmd += 1
        
        # Calcular GMD médio
        gmd_medio = 0
        if animais_com_gmd > 0:
            gmd_medio = gmd_total / animais_com_gmd
        
        # Calcular produção por hectare
        # Obter área total das fazendas
        area_total = 0
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            # Se uma fazenda específica foi selecionada
            fazenda = Fazenda.objects.filter(id=fazenda_id, usuario=usuario).first()
            if fazenda:
                area_total = fazenda.area_total or 0
        else:
            # Se nenhuma fazenda foi selecionada, somar área de todas as fazendas
            fazendas = Fazenda.objects.filter(usuario=usuario)
            for fazenda in fazendas:
                area_total += fazenda.area_total or 0
        
        # Obter produção (kg de carne) nos últimos 12 meses
        # Considerar vendas e abates
        producao_total = 0
        
        # Vendas
        vendas = Venda.objects.filter(
            data__gte=data_inicial_prod,
            data__lte=hoje,
            **filtro_usuario
        )
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            vendas = vendas.filter(
                animais__animal__fazenda_atual_id=fazenda_id
            ).distinct()
        
        for venda in vendas:
            for item in venda.animais.all():
                if item.animal and item.peso_saida:
                    producao_total += item.peso_saida
        
        # Abates
        abates = Abate.objects.filter(
            data__gte=data_inicial_prod,
            data__lte=hoje,
            **filtro_usuario
        )
        
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            abates = abates.filter(
                animais__animal__fazenda_atual_id=fazenda_id
            ).distinct()
        
        for abate in abates:
            for item in abate.animais.all():
                if item.animal and item.peso_abate:
                    producao_total += item.peso_abate
        
        # Calcular produção por hectare
        producao_por_hectare = 0
        if area_total > 0:
            producao_por_hectare = producao_total / area_total
        
        return {
            'gmd': float(gmd_medio),
            'producao_hectare': float(producao_por_hectare),
            'area_total': float(area_total),
            'producao_total': float(producao_total)
        }
    except Exception as e:
        print(f"Erro ao calcular indicadores globais: {e}")
        return {
            'gmd': 0,
            'producao_hectare': 0,
            'area_total': 0,
            'producao_total': 0,
            'erro': str(e)
        }

@login_required
def api_pastos(request):
    """
    API para obter dados dos pastos para o mapa
    """
    try:
        # Obter ID da fazenda do parâmetro da URL ou da sessão
        fazenda_id = request.GET.get('fazenda_id') or request.session.get('fazenda_id')
        
        # Filtrar pastos pela fazenda
        filtro = {'fazenda__usuario': request.user}
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro['fazenda_id'] = fazenda_id
        
        # Obter todos os pastos
        pastos = Pasto.objects.filter(**filtro)
        
        # Preparar dados para o JSON
        dados_pastos = []
        for pasto in pastos:
            # Verificar se o pasto tem coordenadas
            coordenadas = getattr(pasto, 'coordenadas', None)
            if coordenadas:
                # Adicionar dados do pasto
                dados_pastos.append({
                    'id_pasto': pasto.id_pasto,
                    'nome': getattr(pasto, 'nome', None) or f"Pasto {pasto.id_pasto}",
                    'fazenda_id': pasto.fazenda.id_fazenda,
                    'fazenda_nome': pasto.fazenda.nome,
                    'coordenadas': coordenadas,
                    'area': float(getattr(pasto, 'area', 0) or 0),
                    'capacidade_ua': float(getattr(pasto, 'capacidade_ua', 0) or 0),
                    'variedade_capim': getattr(pasto, 'variedade_capim', '') or ''
                })
        
        # Retornar os dados como JSON
        return JsonResponse(dados_pastos, safe=False)
    
    except Exception as e:
        logger.error(f"Erro na API de pastos: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def diagnostico_simples(request):
    """
    Página de diagnóstico simples para verificar o funcionamento do sistema
    """
    return render(request, 'diagnostico_simples.html')

@login_required
def pagina_teste(request):
    """
    Página de teste para desenvolvimento
    """
    return render(request, 'pagina_teste.html')

@login_required
def obter_dados_dashboard_simples(request):
    """
    Endpoint para fornecer dados para o dashboard via AJAX
    """
    try:
        # Obter parâmetros da requisição
        fazenda_id = request.GET.get('fazenda')
        
        # Obter dados do usuário
        usuario = request.user
        
        # Contagem de animais por situação
        filtro_base = {'usuario': usuario}
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            filtro_base['fazenda_atual_id'] = fazenda_id
        
        animais_ativos = Animal.objects.filter(situacao='ATIVO', **filtro_base).count()
        animais_vendidos = Animal.objects.filter(situacao='VENDIDO', **filtro_base).count()
        animais_abatidos = Animal.objects.filter(situacao='ABATIDO', **filtro_base).count()
        animais_mortos = Animal.objects.filter(situacao='MORTO', **filtro_base).count()
        total_animais = animais_ativos + animais_vendidos + animais_abatidos + animais_mortos
        
        # Distribuição por lotes
        distribuicao_lotes = []
        lotes = Lote.objects.filter(fazenda__usuario=usuario)
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            lotes = lotes.filter(fazenda_id=fazenda_id)
        
        for lote in lotes:
            qtd_animais = Animal.objects.filter(lote=lote, situacao='ATIVO').count()
            if qtd_animais > 0:
                distribuicao_lotes.append({
                    'nome': lote.id_lote,
                    'quantidade': qtd_animais,
                    'cor': f'#{hash(lote.id_lote) % 0xFFFFFF:06x}'  # Gera cor baseada no ID do lote
                })
        
        # Distribuição por pastos
        distribuicao_pastos = []
        pastos = Pasto.objects.filter(fazenda__usuario=usuario)
        if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
            pastos = pastos.filter(fazenda_id=fazenda_id)
        
        # Incluir todos os pastos, mesmo aqueles sem animais
        for pasto in pastos:
            qtd_animais = Animal.objects.filter(pasto_atual=pasto, situacao='ATIVO').count()
            # Incluir todos os pastos, mesmo que não tenham animais
            distribuicao_pastos.append({
                'nome': pasto.nome if pasto.nome else f'Pasto {pasto.id_pasto}',
                'quantidade': qtd_animais,
                'cor': f'#{hash(pasto.id_pasto) % 0xFFFFFF:06x}'  # Gera cor baseada no ID do pasto
            })
        
        # Dados financeiros
        dados_financeiros = obter_dados_financeiros(usuario, fazenda_id)
        
        # Indicadores globais
        indicadores_globais = obter_indicadores_globais(usuario, fazenda_id)
        
        # Dados de pesagem
        dados_pesagem = {
            'ultima_data': None,
            'peso_medio': None,
            'total_pesado': 0
        }
        
        # Obter a data da última pesagem
        ultima_pesagem = Pesagem.objects.filter(animal__usuario=usuario).order_by('-data').first()
        if ultima_pesagem:
            dados_pesagem['ultima_data'] = ultima_pesagem.data.strftime('%d/%m/%Y')
            
            # Calcular peso médio das pesagens mais recentes de cada animal
            animais_ids = Animal.objects.filter(situacao='ATIVO', **filtro_base).values_list('id', flat=True)
            
            # Subconsulta para obter a pesagem mais recente de cada animal
            ultimas_pesagens = {}
            for animal_id in animais_ids:
                pesagem = Pesagem.objects.filter(animal_id=animal_id).order_by('-data').first()
                if pesagem:
                    ultimas_pesagens[animal_id] = pesagem
            
            # Calcular média
            if ultimas_pesagens:
                peso_total = sum(p.peso for p in ultimas_pesagens.values())
                dados_pesagem['peso_medio'] = peso_total / len(ultimas_pesagens)
                dados_pesagem['total_pesado'] = len(ultimas_pesagens)
        
        # Montar resposta
        response_data = {
            'contagem_animais': {
                'total': total_animais,
                'ativos': animais_ativos,
                'vendidos': animais_vendidos,
                'abatidos': animais_abatidos,
                'mortos': animais_mortos
            },
            'distribuicao_lotes': distribuicao_lotes,
            'distribuicao_pastos': distribuicao_pastos,
            'dados_financeiros': dados_financeiros,
            'indicadores_globais': indicadores_globais,
            'dados_pesagem': dados_pesagem,
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        import traceback
        print(f"Erro ao obter dados do dashboard: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
