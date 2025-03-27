from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q, Value, CharField, DecimalField
from django.db.models.functions import Coalesce, TruncMonth, ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import datetime, timedelta, date, time
import datetime as dt
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import re
from django.http import JsonResponse
from core.models import Fazenda, Despesa, MovimentacaoNaoOperacional
from core.models_vendas import Venda
from core.models_abates import Abate, PagamentoParcelaAbate
from core.models_compras import Compra
from core.models_parcelas import PagamentoParcela
from core.models_pagamentos_venda import PagamentoVenda

# Filtro personalizado para acessar itens de dicionário por chave
def get_dict_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key, 0)

def register_get_dict_item():
    from django.template.defaulttags import register
    register.filter('get_dict_item', get_dict_item)

@login_required
def relatorio_fluxo_caixa(request):
    """
    Página do Fluxo de Caixa - Regime de Caixa (entradas e saídas efetivas)
    """
    try:
        register_get_dict_item()
        # Obtém os parâmetros da URL
        mes_ano = request.GET.get('mes_ano', '')
        fazenda_id = request.GET.get('fazenda', None)
        
        # Valida o formato do mês/ano
        if mes_ano and not re.match(r'^\d{4}-\d{2}$', mes_ano):
            messages.error(request, 'Formato de mês/ano inválido. Use o formato YYYY-MM.')
            return redirect('relatorio_fluxo_caixa')
        
        # Define as datas inicial e final
        data_inicial = None
        data_final = None
        dados_fluxo = None
        
        if mes_ano:
            # Converte para data
            ano, mes = mes_ano.split('-')
            data_inicial = datetime(int(ano), int(mes), 1)
            
            # Calcula a data final (último dia do mês seguinte + 11 meses)
            if int(mes) == 12:
                data_final = datetime(int(ano) + 1, 12, 31)
            else:
                # Último dia do mês + 11 meses
                ultimo_dia = monthrange(int(ano), int(mes))[1]
                data_inicial_mes = datetime(int(ano), int(mes), 1)
                data_final = (data_inicial_mes + relativedelta(months=+11, day=31))
            
            # Obtém os dados do fluxo de caixa apenas se o filtro de mês/ano for fornecido
            usuario = request.user
            dados_fluxo = processar_dados_fluxo_caixa(usuario, data_inicial, data_final, fazenda_id)
        else:
            # Se não foi fornecido mês/ano, usa o mês atual apenas para preencher o campo
            hoje = datetime.now()
            mes_ano = f"{hoje.year}-{hoje.month:02d}"
        
        # Obtém todas as fazendas do usuário para o filtro
        fazendas = Fazenda.objects.filter(usuario=request.user).order_by('nome')
        
        # Prepara o contexto
        context = {
            'dados_fluxo': dados_fluxo,
            'fazendas': fazendas,
            'filtros': {
                'data_inicial': data_inicial,
                'data_final': data_final,
                'mes_ano': mes_ano,
            },
        }
        
        return render(request, 'Relatorios/fluxo_caixa.html', context)
    
    except Exception as e:
        # Em caso de erro, exibe uma mensagem e retorna para a página
        context = {
            'fazendas': Fazenda.objects.filter(usuario=request.user).order_by('nome'),
            'mensagem_erro': str(e)
        }
        return render(request, 'Relatorios/fluxo_caixa.html', context)

@login_required
def fluxo_caixa_mensal(request):
    """
    View para exibir o fluxo de caixa mensal
    """
    try:
        # Obtém os parâmetros da URL
        mes_ano = request.GET.get('mes_ano', '')
        fazenda_id = request.GET.get('fazenda_id', None)
        
        # Valida o formato do mês/ano
        if not mes_ano or not re.match(r'^\d{4}-\d{2}$', mes_ano):
            messages.error(request, 'Formato de mês/ano inválido. Use o formato YYYY-MM.')
            return redirect('fluxo_caixa')
        
        # Converte para data
        ano, mes = mes_ano.split('-')
        data_inicial = datetime(int(ano), int(mes), 1)
        
        # Calcula a data final (último dia do mês seguinte + 11 meses)
        if int(mes) == 12:
            data_final = datetime(int(ano) + 1, 12, 31)
        else:
            # Último dia do mês + 11 meses
            ultimo_dia = monthrange(int(ano), int(mes))[1]
            data_inicial_mes = datetime(int(ano), int(mes), 1)
            data_final = (data_inicial_mes + relativedelta(months=+11, day=31))
        
        # Obtém os dados do fluxo de caixa
        usuario = request.user
        dados_fluxo = processar_dados_fluxo_caixa(usuario, data_inicial, data_final, fazenda_id)
        
        # Obtém a fazenda selecionada
        fazenda_selecionada = None
        if fazenda_id:
            try:
                fazenda_selecionada = Fazenda.objects.get(id=fazenda_id, usuario=usuario)
            except Fazenda.DoesNotExist:
                pass
        
        # Obtém todas as fazendas do usuário para o filtro
        fazendas = Fazenda.objects.filter(usuario=usuario).order_by('nome')
        
        # Prepara o contexto
        context = {
            'dados_fluxo': dados_fluxo,
            'filtros': {
                'data_inicial': data_inicial,
                'data_final': data_final,
                'mes_ano': mes_ano,
            },
            'fazendas': fazendas,
            'fazenda_selecionada': fazenda_selecionada,
        }
        
        return render(request, 'Relatorios/fluxo_caixa_mensal.html', context)
    
    except Exception as e:
        messages.error(request, f'Erro ao gerar relatório de fluxo de caixa: {str(e)}')
        return redirect('relatorio_fluxo_caixa')

@login_required
def fluxo_caixa_mensal_print(request):
    """
    View para impressão do fluxo de caixa mensal
    """
    try:
        # Obtém os parâmetros da URL
        mes_ano = request.GET.get('mes_ano', '')
        fazenda_id = request.GET.get('fazenda_id', None)
        
        # Valida o formato do mês/ano
        if not mes_ano or not re.match(r'^\d{4}-\d{2}$', mes_ano):
            messages.error(request, 'Formato de mês/ano inválido. Use o formato YYYY-MM.')
            return redirect('fluxo_caixa')
        
        # Converte para data
        ano, mes = mes_ano.split('-')
        data_inicial = datetime(int(ano), int(mes), 1)
        
        # Calcula a data final (último dia do mês seguinte + 11 meses)
        if int(mes) == 12:
            data_final = datetime(int(ano) + 1, 12, 31)
        else:
            # Último dia do mês + 11 meses
            ultimo_dia = monthrange(int(ano), int(mes))[1]
            data_inicial_mes = datetime(int(ano), int(mes), 1)
            data_final = (data_inicial_mes + relativedelta(months=+11, day=31))
        
        # Obtém os dados do fluxo de caixa
        usuario = request.user
        dados_fluxo = processar_dados_fluxo_caixa(usuario, data_inicial, data_final, fazenda_id)
        
        # Obtém a fazenda selecionada
        fazenda_selecionada = None
        if fazenda_id:
            try:
                fazenda_selecionada = Fazenda.objects.get(id=fazenda_id, usuario=usuario)
            except Fazenda.DoesNotExist:
                pass
        
        # Prepara o contexto
        context = {
            'dados_fluxo': dados_fluxo,
            'filtros': {
                'data_inicial': data_inicial,
                'data_final': data_final,
                'mes_ano': mes_ano,
            },
            'fazenda_selecionada': fazenda_selecionada,
        }
        
        return render(request, 'impressao/fluxo_caixa_mensal_print.html', context)
    
    except Exception as e:
        messages.error(request, f'Erro ao gerar relatório de fluxo de caixa: {str(e)}')
        return redirect('fluxo_caixa')

def processar_dados_fluxo_caixa(usuario, data_inicial, data_final, fazenda_id=None):
    """
    Função auxiliar para processar os dados do Fluxo de Caixa
    Diferente do DRE, aqui consideramos o regime de caixa (data de pagamento/recebimento)
    """
    print(f"Período do Fluxo de Caixa: {data_inicial} a {data_final}")
    
    # Converter para date para garantir consistência
    if isinstance(data_inicial, datetime):
        data_inicial = data_inicial.date()
    if isinstance(data_final, datetime):
        data_final = data_final.date()
    
    # Criar estrutura para armazenar dados por mês
    from calendar import month_name
    import locale
    
    # Configurar locale para português
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except:
            pass
    
    # Gerar lista de meses no período
    meses = []
    mes_atual = date(data_inicial.year, data_inicial.month, 1)
    while mes_atual <= data_final:
        nome_mes = mes_atual.strftime('%b/%Y')
        ultimo_dia = monthrange(mes_atual.year, mes_atual.month)[1]
        data_fim = date(mes_atual.year, mes_atual.month, ultimo_dia)
        
        meses.append({
            'nome': nome_mes,
            'data_inicio': mes_atual,
            'data_fim': data_fim
        })
        
        # Avançar para o próximo mês
        if mes_atual.month == 12:
            mes_atual = date(mes_atual.year + 1, 1, 1)
        else:
            mes_atual = date(mes_atual.year, mes_atual.month + 1, 1)
    
    # Inicializar estrutura de dados por mês
    dados_mensais = {}
    for mes in meses:
        dados_mensais[mes['nome']] = {
            'saldo_inicial': 0,
            'entradas_vendas': 0,
            'entradas_abates': 0,
            'entradas_nao_operacionais': 0,
            'saidas_custos_fixos': 0,
            'saidas_custos_variaveis': 0,
            'saidas_compra_animais': 0,
            'saidas_investimentos': 0,
            'saidas_nao_operacionais': 0
        }
    
    # 1. SALDO INICIAL - Calculado como o saldo anterior à data inicial
    # Isso requer uma consulta de todos os pagamentos e recebimentos anteriores à data inicial
    
    # Recebimentos anteriores à data inicial
    filtro_recebimentos_anteriores_vendas = {
        'usuario': usuario,
        'data__lt': data_inicial
    }
    
    # Precisamos calcular o total das vendas anteriores somando os valores dos animais
    vendas_anteriores = Venda.objects.filter(**filtro_recebimentos_anteriores_vendas)
    total_recebimentos_anteriores_vendas = 0
    
    # Somamos os valores dos animais de cada venda
    for venda in vendas_anteriores:
        # Se temos um filtro de fazenda, verificamos se algum animal da venda pertence à fazenda
        if fazenda_id:
            animais_da_fazenda = venda.animais.filter(animal__fazenda_atual_id=fazenda_id)
            if animais_da_fazenda.exists():
                total_recebimentos_anteriores_vendas += float(sum(float(animal.valor_total) for animal in animais_da_fazenda))
        else:
            total_recebimentos_anteriores_vendas += float(sum(float(animal.valor_total) for animal in venda.animais.all()))
    
    filtro_recebimentos_anteriores_abates = {
        'usuario': usuario,
        'data__lt': data_inicial
    }
    
    # Precisamos calcular o total dos abates anteriores somando os valores dos animais
    abates_anteriores = Abate.objects.filter(**filtro_recebimentos_anteriores_abates)
    total_recebimentos_anteriores_abates = 0
    
    # Somamos os valores dos animais de cada abate
    for abate in abates_anteriores:
        # Se temos um filtro de fazenda, verificamos se algum animal do abate pertence à fazenda
        if fazenda_id:
            animais_da_fazenda = abate.animais.filter(animal__fazenda_atual_id=fazenda_id)
            if animais_da_fazenda.exists():
                total_recebimentos_anteriores_abates += float(sum(float(animal.valor_total) for animal in animais_da_fazenda))
        else:
            total_recebimentos_anteriores_abates += float(sum(float(animal.valor_total) for animal in abate.animais.all()))
    
    filtro_recebimentos_anteriores_nao_op = {
        'usuario': usuario,
        'data__lt': data_inicial,
        'valor__gt': 0  # Apenas entradas (valores positivos)
    }
    if fazenda_id and hasattr(MovimentacaoNaoOperacional, 'fazenda'):
        filtro_recebimentos_anteriores_nao_op['fazenda'] = fazenda_id
        
    total_recebimentos_anteriores_nao_op = MovimentacaoNaoOperacional.objects.filter(
        **filtro_recebimentos_anteriores_nao_op
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    total_recebimentos_anteriores = float(total_recebimentos_anteriores_vendas) + float(total_recebimentos_anteriores_abates) + float(total_recebimentos_anteriores_nao_op)
    
    # Pagamentos anteriores à data inicial
    filtro_pagamentos_anteriores_compras = {
        'usuario': usuario,
        'data_pagamento__lt': data_inicial
    }
    
    compras_anteriores = Compra.objects.filter(**filtro_pagamentos_anteriores_compras)
    total_pagamentos_anteriores_compras = 0
    
    # Somamos os valores das compras
    for compra in compras_anteriores:
        # Se temos um filtro de fazenda, verificamos se algum animal da compra pertence à fazenda
        if fazenda_id:
            animais_da_fazenda = compra.animais.filter(animal__fazenda_atual_id=fazenda_id)
            if animais_da_fazenda.exists():
                total_pagamentos_anteriores_compras += float(sum(float(animal.valor_total) for animal in animais_da_fazenda))
        else:
            total_pagamentos_anteriores_compras += float(compra.valor_total)
    
    # Pagamentos anteriores à data inicial
    # Não podemos filtrar diretamente por usuário no PagamentoParcela
    # Precisamos filtrar através da relação com ParcelaCompra
    pagamentos_anteriores = PagamentoParcela.objects.filter(
        data_pagamento__lt=data_inicial,
        parcela__compra__usuario=usuario  # Filtrar pelo usuário da compra associada à parcela
    )
    
    total_pagamentos_anteriores = 0
    if fazenda_id:
        # Filtrar pagamentos por fazenda
        for pagamento in pagamentos_anteriores:
            # Verificar se o pagamento está associado a uma compra/despesa da fazenda especificada
            if hasattr(pagamento.parcela, 'compra') and pagamento.parcela.compra.fazenda == fazenda_id:
                total_pagamentos_anteriores += float(pagamento.valor or 0)
    else:
        # Somar todos os pagamentos do usuário
        total_pagamentos_anteriores = pagamentos_anteriores.aggregate(total=Sum('valor'))['total'] or 0
    
    # Saldo inicial é a diferença entre recebimentos e pagamentos anteriores
    saldo_inicial = float(total_recebimentos_anteriores) - float(total_pagamentos_anteriores) - float(total_pagamentos_anteriores_compras)
    
    # Definir o saldo inicial para o primeiro mês
    if meses:
        dados_mensais[meses[0]['nome']]['saldo_inicial'] = saldo_inicial
    
    # Calcular saldo inicial para os meses seguintes (será o saldo final do mês anterior)
    for i in range(1, len(meses)):
        mes_anterior = meses[i-1]['nome']
        mes_atual = meses[i]['nome']
        
        # Calcular entradas e saídas do mês anterior
        entradas_mes_anterior = (
            dados_mensais[mes_anterior]['entradas_vendas'] +
            dados_mensais[mes_anterior]['entradas_abates'] +
            dados_mensais[mes_anterior]['entradas_nao_operacionais']
        )
        
        saidas_mes_anterior = (
            dados_mensais[mes_anterior]['saidas_custos_fixos'] +
            dados_mensais[mes_anterior]['saidas_custos_variaveis'] +
            dados_mensais[mes_anterior]['saidas_compra_animais'] +
            dados_mensais[mes_anterior]['saidas_investimentos'] +
            dados_mensais[mes_anterior]['saidas_nao_operacionais']
        )
        
        # Calcular fluxo líquido do mês anterior
        fluxo_liquido_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
        
        # Saldo inicial do mês atual = saldo inicial do mês anterior + fluxo líquido do mês anterior
        dados_mensais[mes_atual]['saldo_inicial'] = dados_mensais[mes_anterior]['saldo_inicial'] + fluxo_liquido_mes_anterior
    
    # 2. ENTRADAS DE CAIXA (Recebimentos no período)
    
    # 2.1 Entradas Operacionais
    
    # Recebimentos de vendas no período
    filtro_recebimentos_vendas = {
        'usuario': usuario,
        'data__range': [data_inicial, data_final],
    }
    
    # Precisamos calcular o total das vendas somando os valores dos animais
    vendas_no_periodo = Venda.objects.filter(**filtro_recebimentos_vendas)
    entradas_vendas = 0
    
    # Somamos os valores dos animais de cada venda
    for venda in vendas_no_periodo:
        # Se temos um filtro de fazenda, verificamos se algum animal da venda pertence à fazenda
        if fazenda_id:
            animais_da_fazenda = venda.animais.filter(animal__fazenda_atual_id=fazenda_id)
            if animais_da_fazenda.exists():
                valor_venda = float(sum(float(animal.valor_total) for animal in animais_da_fazenda))
                entradas_vendas += valor_venda
                
                # Adicionar ao mês correspondente
                for mes in meses:
                    if mes['data_inicio'] <= venda.data <= mes['data_fim']:
                        dados_mensais[mes['nome']]['entradas_vendas'] += valor_venda
                        break
        else:
            valor_venda = float(sum(float(animal.valor_total) for animal in venda.animais.all()))
            entradas_vendas += valor_venda
            
            # Adicionar ao mês correspondente
            for mes in meses:
                if mes['data_inicio'] <= venda.data <= mes['data_fim']:
                    dados_mensais[mes['nome']]['entradas_vendas'] += valor_venda
                    break
    
    # Recebimentos de abates no período
    filtro_recebimentos_abates = {
        'usuario': usuario,
        'data__range': [data_inicial, data_final],
    }
    
    # Precisamos calcular o total dos abates somando os valores dos animais
    abates_no_periodo = Abate.objects.filter(**filtro_recebimentos_abates)
    entradas_abates = 0
    
    # Somamos os valores dos animais de cada abate
    for abate in abates_no_periodo:
        # Se temos um filtro de fazenda, verificamos se algum animal do abate pertence à fazenda
        if fazenda_id:
            animais_da_fazenda = abate.animais.filter(animal__fazenda_atual_id=fazenda_id)
            if animais_da_fazenda.exists():
                valor_abate = float(sum(float(animal.valor_total) for animal in animais_da_fazenda))
                entradas_abates += valor_abate
                
                # Adicionar ao mês correspondente
                for mes in meses:
                    if mes['data_inicio'] <= abate.data <= mes['data_fim']:
                        dados_mensais[mes['nome']]['entradas_abates'] += valor_abate
                        break
        else:
            valor_abate = float(sum(float(animal.valor_total) for animal in abate.animais.all()))
            entradas_abates += valor_abate
            
            # Adicionar ao mês correspondente
            for mes in meses:
                if mes['data_inicio'] <= abate.data <= mes['data_fim']:
                    dados_mensais[mes['nome']]['entradas_abates'] += valor_abate
                    break
    
    # Total de entradas operacionais
    entradas_operacionais = float(entradas_vendas) + float(entradas_abates)
    
    # 2.2 Entradas Não Operacionais
    filtro_entradas_nao_op = {
        'usuario': usuario,
        'data__range': [data_inicial, data_final],
        'valor__gt': 0  # Apenas entradas (valores positivos)
    }
    if fazenda_id and hasattr(MovimentacaoNaoOperacional, 'fazenda'):
        filtro_entradas_nao_op['fazenda'] = fazenda_id
        
    entradas_nao_operacionais_query = MovimentacaoNaoOperacional.objects.filter(**filtro_entradas_nao_op)
    entradas_nao_operacionais = entradas_nao_operacionais_query.aggregate(total=Sum('valor'))['total'] or 0
    entradas_nao_operacionais = float(entradas_nao_operacionais)
    
    # Adicionar entradas não operacionais aos meses correspondentes
    for mov in entradas_nao_operacionais_query:
        for mes in meses:
            if mes['data_inicio'] <= mov.data <= mes['data_fim']:
                dados_mensais[mes['nome']]['entradas_nao_operacionais'] += float(mov.valor)
                break
    
    # Total de entradas
    total_entradas = float(entradas_operacionais) + float(entradas_nao_operacionais)
    
    # 3. SAÍDAS DE CAIXA (Pagamentos no período)
    
    # 3.1 Saídas Operacionais
    
    # Pagamentos de despesas fixas e variáveis
    filtro_despesas = {
        'usuario': usuario,
        'data_pagamento__range': [data_inicial, data_final],
        'status': 'PAGO'
    }
    
    # Obter todas as despesas pagas no período
    despesas_no_periodo = Despesa.objects.filter(**filtro_despesas)
    
    saidas_custos_fixos = 0
    saidas_custos_variaveis = 0
    custos_fixos = []
    custos_variaveis = []
    
    # Processar as despesas
    for despesa in despesas_no_periodo:
        # Verificar se a despesa tem categoria
        try:
            categoria = despesa.categoria
            tipo_custo = getattr(categoria, 'tipo', 'fixo')  # Default para 'fixo' se não tiver tipo
        except:
            tipo_custo = 'fixo'  # Default para 'fixo' se não tiver categoria
        
        valor_despesa = float(despesa.valor_total if hasattr(despesa, 'valor_total') else 
                             (despesa.valor if hasattr(despesa, 'valor') else 0))
        
        # Se houver filtro por fazenda, verificar se a despesa está associada à fazenda
        if fazenda_id and hasattr(despesa, 'fazenda') and despesa.fazenda.id != int(fazenda_id):
            continue
        
        # Adicionar ao tipo de custo correspondente
        if tipo_custo == 'variavel':
            saidas_custos_variaveis += valor_despesa
            
            # Adicionar ao mês correspondente
            for mes in meses:
                if mes['data_inicio'] <= despesa.data_pagamento <= mes['data_fim']:
                    dados_mensais[mes['nome']]['saidas_custos_variaveis'] += valor_despesa
                    break
            
            # Adicionar à lista de custos variáveis
            categoria_nome = getattr(categoria, 'nome', 'Sem categoria') if 'categoria' in locals() else 'Sem categoria'
            custos_variaveis.append({
                'descricao': f"{despesa.contato.nome if hasattr(despesa, 'contato') else 'Despesa'} - {categoria_nome}",
                'valor': valor_despesa,
                'data': despesa.data_pagamento
            })
        else:
            saidas_custos_fixos += valor_despesa
            
            # Adicionar ao mês correspondente
            for mes in meses:
                if mes['data_inicio'] <= despesa.data_pagamento <= mes['data_fim']:
                    dados_mensais[mes['nome']]['saidas_custos_fixos'] += valor_despesa
                    break
            
            # Adicionar à lista de custos fixos
            categoria_nome = getattr(categoria, 'nome', 'Sem categoria') if 'categoria' in locals() else 'Sem categoria'
            custos_fixos.append({
                'descricao': f"{despesa.contato.nome if hasattr(despesa, 'contato') else 'Despesa'} - {categoria_nome}",
                'valor': valor_despesa,
                'data': despesa.data_pagamento
            })
    
    # Total de saídas operacionais
    saidas_operacionais = float(saidas_custos_fixos) + float(saidas_custos_variaveis)
    
    # 3.2 Saídas para Investimentos
    
    # Pagamentos de compras de animais
    filtro_pagamentos_compra_animais = {
        'parcela__compra__usuario': usuario,
        'data_pagamento__range': [data_inicial, data_final],
    }
    
    pagamentos_compra_animais = PagamentoParcela.objects.filter(
        parcela__compra__usuario=usuario,
        data_pagamento__range=[data_inicial, data_final],
        parcela__compra__animais__isnull=False  # Compras que têm animais associados
    ).distinct()
    
    saidas_compra_animais = 0
    compras_animais = []
    
    if fazenda_id:
        for pagamento in pagamentos_compra_animais:
            # Verificar se o pagamento está associado a uma compra com animais da fazenda especificada
            if hasattr(pagamento.parcela, 'compra') and pagamento.parcela.compra.fazenda == fazenda_id:
                valor_pagamento = float(pagamento.valor or 0)
                saidas_compra_animais += valor_pagamento
                
                # Adicionar ao mês correspondente
                for mes in meses:
                    if mes['data_inicio'] <= pagamento.data_pagamento <= mes['data_fim']:
                        dados_mensais[mes['nome']]['saidas_compra_animais'] += valor_pagamento
                        break
                
                # Adicionar à lista de compras de animais
                if pagamento.parcela.compra not in [item['compra'] for item in compras_animais]:
                    compras_animais.append({
                        'compra': pagamento.parcela.compra,
                        'valor': valor_pagamento,
                        'data': pagamento.data_pagamento
                    })
                else:
                    # Somar ao item existente
                    for item in compras_animais:
                        if item['compra'] == pagamento.parcela.compra:
                            item['valor'] += valor_pagamento
                            break
    else:
        # Sem filtro por fazenda, somamos todos os pagamentos
        saidas_compra_animais = pagamentos_compra_animais.aggregate(total=Sum('valor'))['total'] or 0
        saidas_compra_animais = float(saidas_compra_animais)
        
        # Agrupar por compra
        compras_processadas = set()
        for pagamento in pagamentos_compra_animais:
            compra = pagamento.parcela.compra
            if compra.id not in compras_processadas:
                compras_processadas.add(compra.id)
                
                # Calcular o total pago para esta compra no período
                valor_pago = PagamentoParcela.objects.filter(
                    parcela__compra=compra,
                    data_pagamento__range=[data_inicial, data_final]
                ).aggregate(total=Sum('valor'))['total'] or 0
                
                compras_animais.append({
                    'compra': compra,
                    'valor': float(valor_pago),
                    'data': pagamento.data_pagamento
                })
    
    # Ordenar compras de animais por valor (maior para menor)
    compras_animais.sort(key=lambda x: x['valor'], reverse=True)
    
    # Pagamentos de outros investimentos
    filtro_pagamentos_investimentos = {
        'usuario': usuario,
        'data_pagamento__range': [data_inicial, data_final],
    }
    
    pagamentos_investimentos = PagamentoParcela.objects.filter(
        parcela__compra__usuario=usuario,
        data_pagamento__range=[data_inicial, data_final]
    )
    
    saidas_investimentos_outros = 0
    investimentos = []
    
    if fazenda_id:
        for pagamento in pagamentos_investimentos:
            # Verificar se o pagamento está associado a uma compra com animais da fazenda especificada
            if hasattr(pagamento.parcela, 'compra') and pagamento.parcela.compra.fazenda == fazenda_id:
                saidas_investimentos_outros += float(pagamento.valor or 0)
                
                # Adicionar ao mês correspondente
                for mes in meses:
                    if mes['data_inicio'] <= pagamento.data_pagamento <= mes['data_fim']:
                        dados_mensais[mes['nome']]['saidas_investimentos'] += float(pagamento.valor or 0)
                        break
                
                # Adicionar à lista de investimentos
                if pagamento.parcela.compra not in [item['compra'] for item in investimentos]:
                    investimentos.append({
                        'compra': pagamento.parcela.compra,
                        'valor': float(pagamento.valor or 0),
                        'data': pagamento.data_pagamento
                    })
                else:
                    # Somar ao item existente
                    for item in investimentos:
                        if item['compra'] == pagamento.parcela.compra:
                            item['valor'] += float(pagamento.valor or 0)
                            break
    else:
        # Sem filtro por fazenda, somamos todos os pagamentos
        saidas_investimentos_outros = pagamentos_investimentos.aggregate(total=Sum('valor'))['total'] or 0
        saidas_investimentos_outros = float(saidas_investimentos_outros)
        
        # Agrupar por compra
        compras_processadas = set()
        for pagamento in pagamentos_investimentos:
            compra = pagamento.parcela.compra
            if compra.id not in compras_processadas:
                compras_processadas.add(compra.id)
                
                # Calcular o total pago para esta compra no período
                valor_pago = PagamentoParcela.objects.filter(
                    parcela__compra=compra,
                    data_pagamento__range=[data_inicial, data_final]
                ).aggregate(total=Sum('valor'))['total'] or 0
                
                investimentos.append({
                    'compra': compra,
                    'valor': float(valor_pago),
                    'data': pagamento.data_pagamento
                })
    
    # Ordenar investimentos por valor (maior para menor)
    investimentos.sort(key=lambda x: x['valor'], reverse=True)
    
    # Total de saídas para investimentos
    saidas_investimentos = float(saidas_compra_animais) + float(saidas_investimentos_outros)
    
    # 3.3 Saídas Não Operacionais
    filtro_saidas_nao_op = {
        'usuario': usuario,
        'data__range': [data_inicial, data_final],
        'valor__lt': 0  # Apenas saídas (valores negativos)
    }
    if fazenda_id and hasattr(MovimentacaoNaoOperacional, 'fazenda'):
        filtro_saidas_nao_op['fazenda'] = fazenda_id
        
    saidas_nao_operacionais_query = MovimentacaoNaoOperacional.objects.filter(
        **filtro_saidas_nao_op
    )
    saidas_nao_operacionais = saidas_nao_operacionais_query.aggregate(total=Sum('valor'))['total'] or 0
    saidas_nao_operacionais = abs(float(saidas_nao_operacionais))  # Convertemos para positivo para somar às saídas
    
    # Adicionar saídas não operacionais aos meses correspondentes
    for mov in saidas_nao_operacionais_query:
        for mes in meses:
            if mes['data_inicio'] <= mov.data <= mes['data_fim']:
                dados_mensais[mes['nome']]['saidas_nao_operacionais'] += abs(float(mov.valor))
                break
    
    # Total de saídas
    total_saidas = float(saidas_operacionais) + float(saidas_investimentos) + float(saidas_nao_operacionais)
    
    # 4. FLUXO DE CAIXA LÍQUIDO (Entradas - Saídas)
    fluxo_liquido = float(total_entradas) - float(total_saidas)
    
    # 5. SALDO FINAL (Saldo Inicial + Fluxo Líquido)
    saldo_final = float(saldo_inicial) + float(fluxo_liquido)
    
    # Calcular percentuais em relação ao total de entradas
    percentual_entradas_vendas = (float(entradas_vendas) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_entradas_abates = (float(entradas_abates) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_entradas_operacionais = (float(entradas_operacionais) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_entradas_nao_operacionais = (float(entradas_nao_operacionais) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    
    percentual_saidas_custos_fixos = (float(saidas_custos_fixos) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_saidas_custos_variaveis = (float(saidas_custos_variaveis) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_saidas_operacionais = (float(saidas_operacionais) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_saidas_compra_animais = (float(saidas_compra_animais) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_saidas_investimentos = (float(saidas_investimentos) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_saidas_nao_operacionais = (float(saidas_nao_operacionais) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    percentual_total_saidas = (float(total_saidas) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    
    percentual_fluxo_liquido = (float(fluxo_liquido) / float(total_entradas)) * 100 if total_entradas > 0 else 0
    
    # Reorganizar os dados para facilitar o uso no template
    dados_por_categoria = {
        'saldo_inicial': {},
        'entradas_vendas': {},
        'entradas_abates': {},
        'entradas_nao_operacionais': {},
        'saidas_custos_fixos': {},
        'saidas_custos_variaveis': {},
        'saidas_compra_animais': {},
        'saidas_investimentos': {},
        'saidas_nao_operacionais': {}
    }
    
    # Preencher os dados por categoria
    for mes_nome, mes_dados in dados_mensais.items():
        for categoria, valor in mes_dados.items():
            dados_por_categoria[categoria][mes_nome] = valor
    
    # Calcular totais por mês
    totais_entradas = {}
    totais_saidas = {}
    fluxo_liquido = {}
    saldo_final = {}
    
    for mes_nome in dados_mensais.keys():
        # Total de entradas
        totais_entradas[mes_nome] = (
            dados_mensais[mes_nome]['entradas_vendas'] +
            dados_mensais[mes_nome]['entradas_abates'] +
            dados_mensais[mes_nome]['entradas_nao_operacionais']
        )
        
        # Total de saídas
        totais_saidas[mes_nome] = (
            dados_mensais[mes_nome]['saidas_custos_fixos'] +
            dados_mensais[mes_nome]['saidas_custos_variaveis'] +
            dados_mensais[mes_nome]['saidas_compra_animais'] +
            dados_mensais[mes_nome]['saidas_investimentos'] +
            dados_mensais[mes_nome]['saidas_nao_operacionais']
        )
        
        # Fluxo líquido
        fluxo_liquido[mes_nome] = totais_entradas[mes_nome] - totais_saidas[mes_nome]
        
        # Saldo final
        saldo_final[mes_nome] = dados_mensais[mes_nome]['saldo_inicial'] + fluxo_liquido[mes_nome]
    
    # Montar resposta
    dados_fluxo = {
        # 1. SALDO INICIAL
        'saldo_inicial': float(saldo_inicial),
        
        # 2. ENTRADAS
        'entradas_vendas': float(entradas_vendas),
        'entradas_abates': float(entradas_abates),
        'entradas_operacionais': float(entradas_operacionais),
        'entradas_nao_operacionais': float(entradas_nao_operacionais),
        'total_entradas': float(total_entradas),
        
        # Percentuais de entradas
        'percentual_entradas_vendas': percentual_entradas_vendas,
        'percentual_entradas_abates': percentual_entradas_abates,
        'percentual_entradas_operacionais': percentual_entradas_operacionais,
        'percentual_entradas_nao_operacionais': percentual_entradas_nao_operacionais,
        
        # 3. SAÍDAS
        'saidas_custos_fixos': float(saidas_custos_fixos),
        'saidas_custos_variaveis': float(saidas_custos_variaveis),
        'saidas_operacionais': float(saidas_operacionais),
        'saidas_compra_animais': float(saidas_compra_animais),
        'saidas_investimentos_outros': float(saidas_investimentos_outros),
        'saidas_investimentos': float(saidas_investimentos),
        'saidas_nao_operacionais': float(saidas_nao_operacionais),
        'total_saidas': float(total_saidas),
        
        # Detalhamento das saídas
        'custos_fixos': custos_fixos,
        'custos_variaveis': custos_variaveis,
        'investimentos': investimentos,
        
        # Percentuais de saídas
        'percentual_saidas_custos_fixos': percentual_saidas_custos_fixos,
        'percentual_saidas_custos_variaveis': percentual_saidas_custos_variaveis,
        'percentual_saidas_operacionais': percentual_saidas_operacionais,
        'percentual_saidas_compra_animais': percentual_saidas_compra_animais,
        'percentual_saidas_investimentos': percentual_saidas_investimentos,
        'percentual_saidas_nao_operacionais': percentual_saidas_nao_operacionais,
        'percentual_total_saidas': percentual_total_saidas,
        
        # 4. FLUXO LÍQUIDO
        'fluxo_liquido': float(fluxo_liquido),
        'percentual_fluxo_liquido': percentual_fluxo_liquido,
        
        # 5. SALDO FINAL
        'saldo_final': float(saldo_final),
        
        # Dados mensais
        'meses': dados_mensais,
        
        # Dados organizados por categoria
        'dados_por_categoria': dados_por_categoria,
        
        # Totais calculados
        'totais_entradas': totais_entradas,
        'totais_saidas': totais_saidas,
        'fluxo_liquido_mensal': fluxo_liquido,
        'saldo_final_mensal': saldo_final,
        
        # Lista de meses para ordenação correta
        'lista_meses': [mes['nome'] for mes in meses]
    }
    
    return dados_fluxo
