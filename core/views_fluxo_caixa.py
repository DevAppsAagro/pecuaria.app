from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q, Count, Case, When, Value, IntegerField, DecimalField
from django.utils import timezone
from django.template.defaulttags import register
from datetime import datetime, timedelta, date
from decimal import Decimal
import calendar
from calendar import monthrange
import locale
import re  # Adicionando importação do módulo re para expressões regulares

# Importações dos modelos
from .models import (
    Animal, Lote, Pesagem, RateioCusto, Fazenda, CategoriaCusto, 
    Despesa, MovimentacaoNaoOperacional, Pasto, Benfeitoria, 
    ExtratoBancario, ManejoSanitario, ManejoReproducao, ContaBancaria
)
from .models_compras import Compra, CompraAnimal
from .models_parcelas import ParcelaCompra, PagamentoParcela
from .models_vendas import Venda, VendaAnimal
from .models_pagamentos_venda import PagamentoVenda
from .models_abates import Abate, AbateAnimal, PagamentoParcelaAbate

# Filtro personalizado para acessar itens de dicionário em templates
@register.filter
def get_dict_item(dictionary, key):
    """
    Filtro para acessar itens de dicionário em templates
    Verifica se o objeto é um dicionário antes de tentar acessar o método get
    """
    if dictionary is None:
        print(f"ERRO: Dicionário é None, chave solicitada: {key}")
        return 0
    
    # Verificar se é um dicionário
    if hasattr(dictionary, 'get'):
        value = dictionary.get(key, 0)
        return value
    
    # Se não for um dicionário, registrar erro e retornar 0
    print(f"ERRO: Objeto não é um dicionário: tipo={type(dictionary)}, valor={dictionary}, chave={key}")
    return 0

# Filtro para subtração em templates
@register.filter
def sub(value, arg):
    """
    Filtro para realizar subtração em templates
    Verifica se os valores são numéricos antes de realizar a operação
    """
    try:
        # Converter para float para garantir que a operação seja possível
        value = float(value) if value is not None else 0
        arg = float(arg) if arg is not None else 0
        return value - arg
    except (ValueError, TypeError) as e:
        print(f"ERRO no filtro sub: {e}, value={value}, arg={arg}")
        return 0

# Filtro para adição segura em templates
@register.filter
def safe_add(value, arg):
    """
    Filtro para realizar adição em templates de forma segura
    Verifica se os valores são numéricos antes de realizar a operação
    """
    try:
        # Converter para float para garantir que a operação seja possível
        value = float(value) if value is not None else 0
        arg = float(arg) if arg is not None else 0
        return value + arg
    except (ValueError, TypeError) as e:
        print(f"ERRO no filtro safe_add: {e}, value={value}, arg={arg}")
        return 0

# Filtro para subtração segura em templates
@register.filter
def safe_sub(value, arg):
    """
    Filtro para realizar subtração em templates de forma segura
    Verifica se os valores são numéricos antes de realizar a operação
    """
    try:
        # Converter para float para garantir que a operação seja possível
        value = float(value) if value is not None else 0
        arg = float(arg) if arg is not None else 0
        return value - arg
    except (ValueError, TypeError) as e:
        print(f"ERRO no filtro safe_sub: {e}, value={value}, arg={arg}")
        return 0

@login_required
def relatorio_fluxo_caixa(request):
    """
    Página principal do Fluxo de Caixa
    """
    print("===== INICIANDO RELATÓRIO DE FLUXO DE CAIXA =====")
    
    # Obtém as fazendas do usuário para filtro
    fazendas = Fazenda.objects.filter(usuario=request.user)
    print(f"Fazendas disponíveis: {[f.nome for f in fazendas]}")
    
    # Filtros
    mes_ano = request.GET.get('mes_ano', '')
    fazenda_id = request.GET.get('fazenda', None)
    
    print(f"Filtros recebidos: mes_ano={mes_ano}, fazenda_id={fazenda_id}")
    
    # Dados do relatório
    dados_fluxo = None
    fazenda_selecionada = None
    
    if mes_ano:
        # Processar filtros e obter dados do relatório
        try:
            # Converter mes_ano para data
            # Verifica se o formato é correto (YYYY-MM)
            if not re.match(r'^\d{4}-\d{1,2}$', mes_ano):
                raise ValueError(f"Formato de data inválido: {mes_ano}. Use o formato YYYY-MM.")
            
            # Extrair ano e mês
            ano, mes = mes_ano.split('-')
            ano = int(ano)
            mes = int(mes)
            
            # Validar mês
            if mes < 1 or mes > 12:
                raise ValueError(f"Mês deve estar entre 1 e 12. Valor recebido: {mes}")
            
            # Criar data inicial
            data_inicial = date(ano, mes, 1)
            print(f"Data inicial convertida: {data_inicial}")
            
            # Calcular data final (12 meses a partir da data inicial)
            ultimo_dia_mes = monthrange(data_inicial.year, data_inicial.month)[1]
            data_final = date(data_inicial.year, data_inicial.month, ultimo_dia_mes)
            
            # Calcular data final 12 meses à frente
            if data_inicial.month + 11 > 12:
                # Se passar de dezembro, ajusta para o próximo ano
                novo_ano = data_inicial.year + 1
                novo_mes = (data_inicial.month + 11) % 12
                if novo_mes == 0:
                    novo_mes = 12
            else:
                novo_ano = data_inicial.year
                novo_mes = data_inicial.month + 11
            
            ultimo_dia_final = monthrange(novo_ano, novo_mes)[1]
            data_final = date(novo_ano, novo_mes, ultimo_dia_final)
            
            print(f"Data final calculada: {data_final}")
            
            # Obter fazenda selecionada se houver
            if fazenda_id:
                try:
                    fazenda_selecionada = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
                    print(f"Fazenda selecionada: {fazenda_selecionada.nome}")
                except Fazenda.DoesNotExist:
                    fazenda_selecionada = None
                    print("Fazenda não encontrada")
            
            # Processar dados do fluxo de caixa
            print("Chamando função processar_dados_fluxo_caixa...")
            dados_fluxo = processar_dados_fluxo_caixa(request.user, data_inicial, data_final, fazenda_selecionada)
            print("Dados do fluxo de caixa processados com sucesso")
            
            # Verificar estrutura dos dados
            if dados_fluxo:
                print(f"Meses gerados: {[mes['nome'] for mes in dados_fluxo['meses']]}")
                print(f"Dados do primeiro mês: {dados_fluxo['dados_mensais'].get(dados_fluxo['meses'][0]['nome'], 'Não encontrado')}")
            
        except ValueError as e:
            print(f"ERRO ao processar datas: {str(e)}")
            messages.error(request, f'Erro ao processar datas: {str(e)}')
    else:
        print("Nenhum mês/ano selecionado, não processando dados")
    
    context = {
        'fazendas': fazendas,
        'dados_fluxo': dados_fluxo,
        'fazenda_selecionada': fazenda_selecionada,
        'filtros': {
            'mes_ano': mes_ano,
            'fazenda': fazenda_id,
        }
    }
    
    print("Renderizando template 'Relatorios/fluxo_caixa_novo.html'")
    return render(request, 'Relatorios/fluxo_caixa_novo.html', context)

@login_required
def imprimir_fluxo_caixa(request):
    """
    Versão para impressão do Fluxo de Caixa
    """
    print("===== INICIANDO IMPRESSÃO DE FLUXO DE CAIXA =====")
    
    # Obtém os parâmetros da URL
    mes_ano = request.GET.get('mes_ano', '')
    fazenda_id = request.GET.get('fazenda', None)
    
    print(f"Parâmetros de impressão: mes_ano={mes_ano}, fazenda_id={fazenda_id}")
    
    # Dados do relatório
    dados_fluxo = None
    fazenda_selecionada = None
    
    try:
        # Verificar formato da data
        if not re.match(r'^\d{4}-\d{1,2}$', mes_ano):
            raise ValueError(f"Formato de data inválido: {mes_ano}. Use o formato YYYY-MM.")
        
        # Extrair ano e mês
        ano, mes = mes_ano.split('-')
        ano = int(ano)
        mes = int(mes)
        
        # Validar mês
        if mes < 1 or mes > 12:
            raise ValueError(f"Mês deve estar entre 1 e 12. Valor recebido: {mes}")
        
        # Criar data inicial
        data_inicial = date(ano, mes, 1)
        print(f"Data inicial de impressão: {data_inicial}")
        
        # Calcular data final (12 meses a partir da data inicial)
        ultimo_dia_mes = monthrange(data_inicial.year, data_inicial.month)[1]
        data_final = date(data_inicial.year, data_inicial.month, ultimo_dia_mes)
        
        # Calcular data final 12 meses à frente
        if data_inicial.month + 11 > 12:
            # Se passar de dezembro, ajusta para o próximo ano
            novo_ano = data_inicial.year + 1
            novo_mes = (data_inicial.month + 11) % 12
            if novo_mes == 0:
                novo_mes = 12
        else:
            novo_ano = data_inicial.year
            novo_mes = data_inicial.month + 11
        
        ultimo_dia_final = monthrange(novo_ano, novo_mes)[1]
        data_final = date(novo_ano, novo_mes, ultimo_dia_final)
        
        print(f"Data final de impressão: {data_final}")
        
        # Obter fazenda selecionada se houver
        if fazenda_id:
            try:
                fazenda_selecionada = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
                print(f"Fazenda selecionada para impressão: {fazenda_selecionada.nome}")
            except Fazenda.DoesNotExist:
                fazenda_selecionada = None
                print("Fazenda para impressão não encontrada")
        
        # Processar dados do fluxo de caixa
        print("Chamando função processar_dados_fluxo_caixa para impressão...")
        dados_fluxo = processar_dados_fluxo_caixa(request.user, data_inicial, data_final, fazenda_selecionada)
        print("Dados do fluxo de caixa para impressão processados com sucesso")
        
        context = {
            'dados_fluxo': dados_fluxo,
            'filtros': {
                'mes_ano': mes_ano,
            },
            'fazenda_selecionada': fazenda_selecionada,
        }
        
        print("Renderizando template de impressão 'Relatorios/fluxo_caixa_novo_print.html'")
        return render(request, 'Relatorios/fluxo_caixa_novo_print.html', context)
    
    except Exception as e:
        print(f"ERRO ao gerar relatório de impressão: {str(e)}")
        messages.error(request, f'Erro ao gerar relatório de fluxo de caixa: {str(e)}')
        return redirect('relatorio_fluxo_caixa')

def processar_dados_fluxo_caixa(usuario, data_inicial, data_final, fazenda=None):
    """
    Função auxiliar para processar os dados do Fluxo de Caixa
    Diferente do DRE, aqui consideramos o regime de caixa (data de pagamento/recebimento)
    """
    print("===== PROCESSANDO DADOS DO FLUXO DE CAIXA =====")
    print(f"Período do Fluxo de Caixa: {data_inicial} a {data_final}")
    print(f"Fazenda: {fazenda.nome if fazenda else 'Todas as fazendas'}")
    
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
        print("Locale configurado para pt_BR.UTF-8")
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            print("Locale configurado para Portuguese_Brazil.1252")
        except:
            print("Não foi possível configurar o locale para português")
            pass
    
    # Gerar lista de meses no período
    meses = []
    mes_atual = date(data_inicial.year, data_inicial.month, 1)
    print(f"Gerando meses a partir de: {mes_atual}")
    
    while mes_atual <= data_final:
        nome_mes = mes_atual.strftime('%b/%Y')
        ultimo_dia = monthrange(mes_atual.year, mes_atual.month)[1]
        data_fim = date(mes_atual.year, mes_atual.month, ultimo_dia)
        
        meses.append({
            'nome': nome_mes,
            'data_inicio': mes_atual,
            'data_fim': data_fim
        })
        
        print(f"Mês adicionado: {nome_mes} ({mes_atual} a {data_fim})")
        
        # Avançar para o próximo mês
        if mes_atual.month == 12:
            mes_atual = date(mes_atual.year + 1, 1, 1)
        else:
            mes_atual = date(mes_atual.year, mes_atual.month + 1, 1)
    
    print(f"Total de meses gerados: {len(meses)}")
    
    # Inicializar estrutura de dados por mês
    dados_mensais = {}
    
    # Adiciona os dados de fluxo de caixa para cada mês
    for mes in meses:
        # Inicializa os dados do mês
        dados_mensais[mes['nome']] = {
            'saldo_inicial': 0,
            'entradas_vendas': 0,
            'entradas_abates': 0,
            'entradas_nao_operacionais': 0,
            'saidas_custos_fixos': 0,
            'saidas_custos_variaveis': 0,
            'saidas_compra_animais': 0,
            'saidas_investimentos': 0,
            'saidas_outros_investimentos': 0,
            'saidas_nao_operacionais': 0,
            'fluxo_liquido': 0,
            'saldo_acumulado': 0
        }

        # Obtém o saldo inicial para o mês
        if mes['nome'] == meses[0]['nome']:  # Primeiro mês
            # Obtém o saldo inicial a partir do extrato bancário
            saldo_inicial = ExtratoBancario.objects.filter(
                usuario=usuario,
                data__lt=mes['data_inicio']
            ).order_by('-data').first()
            
            if saldo_inicial:
                dados_mensais[mes['nome']]['saldo_inicial'] = saldo_inicial.saldo_final
            else:
                dados_mensais[mes['nome']]['saldo_inicial'] = 0
        else:
            # Para os meses seguintes, o saldo inicial é o saldo acumulado do mês anterior
            mes_anterior = meses[meses.index(mes) - 1]['nome']
            dados_mensais[mes['nome']]['saldo_inicial'] = dados_mensais[mes_anterior]['saldo_acumulado']
    
    # Processar dados para cada mês
    for i, mes in enumerate(meses):
        print(f"Processando dados para o mês {mes['nome']}...")
        
        # Datas do mês atual
        data_inicio_mes = mes['data_inicio']
        data_fim_mes = mes['data_fim']
        
        # 1. ENTRADAS DE CAIXA
        
        # 1.1 Entradas: Vendas (usando data de recebimento)
        try:
            # Filtrar pagamentos de parcelas de vendas recebidos no mês
            if fazenda:
                # Filtrar por fazenda
                vendas_ids = VendaAnimal.objects.filter(
                    animal__fazenda_atual=fazenda
                ).values_list('venda_id', flat=True).distinct()
                
                pagamentos_vendas = PagamentoVenda.objects.filter(
                    parcela__venda__id__in=vendas_ids,
                    data_pagamento__range=[data_inicio_mes, data_fim_mes],
                    parcela__venda__usuario=usuario
                )
            else:
                # Todas as fazendas
                pagamentos_vendas = PagamentoVenda.objects.filter(
                    data_pagamento__range=[data_inicio_mes, data_fim_mes],
                    parcela__venda__usuario=usuario
                )
            
            total_vendas = pagamentos_vendas.aggregate(total=Sum('valor'))['total'] or 0
            dados_mensais[mes['nome']]['entradas_vendas'] = float(total_vendas)
            print(f"Entradas de vendas para {mes['nome']}: {total_vendas}")
        except Exception as e:
            print(f"Erro ao processar entradas de vendas: {str(e)}")
        
        # 1.2 Entradas: Abates (usando data de recebimento)
        try:
            # Filtrar pagamentos de parcelas de abates recebidos no mês
            if fazenda:
                # Filtrar por fazenda
                abates_ids = AbateAnimal.objects.filter(
                    animal__fazenda_atual=fazenda
                ).values_list('abate_id', flat=True).distinct()
                
                pagamentos_abates = PagamentoParcelaAbate.objects.filter(
                    parcela__abate__id__in=abates_ids,
                    data_pagamento__range=[data_inicio_mes, data_fim_mes],
                    parcela__abate__usuario=usuario
                )
            else:
                # Todas as fazendas
                pagamentos_abates = PagamentoParcelaAbate.objects.filter(
                    data_pagamento__range=[data_inicio_mes, data_fim_mes],
                    parcela__abate__usuario=usuario
                )
            
            total_abates = pagamentos_abates.aggregate(total=Sum('valor'))['total'] or 0
            dados_mensais[mes['nome']]['entradas_abates'] = float(total_abates)
            print(f"Entradas de abates para {mes['nome']}: {total_abates}")
        except Exception as e:
            print(f"Erro ao processar entradas de abates: {str(e)}")
        
        # 1.3 Entradas: Não Operacionais
        try:
            # Filtrar movimentações não operacionais de entrada no mês
            filtro_entradas_nao_op = {
                'usuario': usuario,
                'data_pagamento__range': [data_inicio_mes, data_fim_mes],
                'tipo': 'entrada'
            }
            if fazenda:
                filtro_entradas_nao_op['fazenda'] = fazenda
            
            entradas_nao_op = MovimentacaoNaoOperacional.objects.filter(**filtro_entradas_nao_op)
            total_entradas_nao_op = entradas_nao_op.aggregate(total=Sum('valor'))['total'] or 0
            dados_mensais[mes['nome']]['entradas_nao_operacionais'] = float(total_entradas_nao_op)
            print(f"Entradas não operacionais para {mes['nome']}: {total_entradas_nao_op}")
        except Exception as e:
            print(f"Erro ao processar entradas não operacionais: {str(e)}")
        
        # 2. SAÍDAS DE CAIXA
        
        # 2.1 Saídas: Custos Fixos (usando data de pagamento)
        try:
            # Filtrar pagamentos de despesas fixas no mês
            filtro_despesas_fixas = {
                'usuario': usuario,
                'itens__categoria__tipo': 'fixo',
                'data_pagamento__range': [data_inicio_mes, data_fim_mes]
            }
            if fazenda:
                filtro_despesas_fixas['itens__fazenda_destino'] = fazenda
            
            despesas_fixas = Despesa.objects.filter(**filtro_despesas_fixas)
            total_custos_fixos = 0
            
            for despesa in despesas_fixas:
                # Calcular o total dos itens de despesa fixos
                itens_fixos = despesa.itens.filter(categoria__tipo='fixo')
                if fazenda:
                    itens_fixos = itens_fixos.filter(fazenda_destino=fazenda)
                
                total_itens_fixos = itens_fixos.aggregate(total=Sum('valor_total'))['total'] or 0
                total_custos_fixos += float(total_itens_fixos)
            
            dados_mensais[mes['nome']]['saidas_custos_fixos'] = total_custos_fixos
            print(f"Saídas de custos fixos para {mes['nome']}: {total_custos_fixos}")
        except Exception as e:
            print(f"Erro ao processar saídas de custos fixos: {str(e)}")
        
        # 2.2 Saídas: Custos Variáveis (usando data de pagamento)
        try:
            # Filtrar pagamentos de despesas variáveis no mês
            filtro_despesas_variaveis = {
                'usuario': usuario,
                'itens__categoria__tipo': 'variavel',
                'data_pagamento__range': [data_inicio_mes, data_fim_mes]
            }
            if fazenda:
                filtro_despesas_variaveis['itens__fazenda_destino'] = fazenda
            
            despesas_variaveis = Despesa.objects.filter(**filtro_despesas_variaveis)
            total_custos_variaveis = 0
            
            for despesa in despesas_variaveis:
                # Calcular o total dos itens de despesa variáveis
                itens_variaveis = despesa.itens.filter(categoria__tipo='variavel')
                if fazenda:
                    itens_variaveis = itens_variaveis.filter(fazenda_destino=fazenda)
                
                total_itens_variaveis = itens_variaveis.aggregate(total=Sum('valor_total'))['total'] or 0
                total_custos_variaveis += float(total_itens_variaveis)
            
            dados_mensais[mes['nome']]['saidas_custos_variaveis'] = total_custos_variaveis
            print(f"Saídas de custos variáveis para {mes['nome']}: {total_custos_variaveis}")
        except Exception as e:
            print(f"Erro ao processar saídas de custos variáveis: {str(e)}")
        
        # 2.3 Saídas: Investimentos (incluindo compra de animais, usando data de pagamento)
        try:
            # 2.3.1 Compra de Animais
            # Seguindo a mesma lógica do DRE para compras de animais
            filtro_compras = {
                'usuario': usuario,
                'data_pagamento__range': [data_inicio_mes, data_fim_mes]  # Usar regime de caixa
            }
            
            # Compras não têm campo 'fazenda' diretamente
            compras = Compra.objects.filter(**filtro_compras)
            
            # Filtramos os animais comprados depois por fazenda, se necessário
            total_compras = 0
            for compra in compras:
                # Se temos um filtro de fazenda, verificamos se os animais estão nessa fazenda
                if fazenda:
                    for animal_compra in compra.animais.all():
                        if animal_compra.animal.fazenda_atual == fazenda:
                            total_compras += float(animal_compra.valor_total or 0)
                else:
                    # Sem filtro de fazenda, somamos todos os valores dos animais
                    total_compras += float(compra.valor_total or 0)
            
            print(f"Total de compras de animais (abordagem DRE): {total_compras}")
            
            # 2.3.2 Outros Investimentos
            # Filtrar pagamentos de despesas de investimento no mês
            filtro_investimentos = {
                'usuario': usuario,
                'itens__categoria__tipo': 'investimento',
                'data_pagamento__range': [data_inicio_mes, data_fim_mes]
            }
            if fazenda:
                filtro_investimentos['itens__fazenda_destino'] = fazenda
            
            despesas_investimentos = Despesa.objects.filter(**filtro_investimentos)
            total_outros_investimentos = 0
            
            for despesa in despesas_investimentos:
                # Calcular o total dos itens de despesa de investimento
                # Excluir despesas que possam estar relacionadas a compras de animais
                # para evitar duplicação
                itens_investimentos = despesa.itens.filter(
                    categoria__tipo='investimento'
                ).exclude(
                    categoria__nome__icontains='compra de animais'
                ).exclude(
                    categoria__nome__icontains='aquisição de animais'
                )
                
                if fazenda:
                    itens_investimentos = itens_investimentos.filter(fazenda_destino=fazenda)
                
                total_itens_investimentos = itens_investimentos.aggregate(total=Sum('valor_total'))['total'] or 0
                total_outros_investimentos += float(total_itens_investimentos)
            
            # Total de investimentos (compra de animais + outros investimentos)
            total_investimentos = float(total_compras) + float(total_outros_investimentos)
            
            # Armazenar os valores separadamente para referência
            dados_mensais[mes['nome']]['saidas_compra_animais'] = float(total_compras)
            dados_mensais[mes['nome']]['saidas_outros_investimentos'] = float(total_outros_investimentos)
            dados_mensais[mes['nome']]['saidas_investimentos'] = float(total_outros_investimentos)  # Apenas outros investimentos
            
            print(f"Saídas de compra de animais para {mes['nome']}: {total_compras}")
            print(f"Saídas de outros investimentos para {mes['nome']}: {total_outros_investimentos}")
            print(f"Total de investimentos para {mes['nome']}: {total_investimentos}")
        except Exception as e:
            print(f"Erro ao processar saídas de investimentos: {str(e)}")
        
        # 2.4 Saídas: Não Operacionais
        try:
            # Filtrar movimentações não operacionais de saída no mês
            filtro_saidas_nao_op = {
                'usuario': usuario,
                'data_pagamento__range': [data_inicio_mes, data_fim_mes],
                'tipo': 'saida'
            }
            if fazenda:
                filtro_saidas_nao_op['fazenda'] = fazenda
            
            saidas_nao_op = MovimentacaoNaoOperacional.objects.filter(**filtro_saidas_nao_op)
            total_saidas_nao_op = saidas_nao_op.aggregate(total=Sum('valor'))['total'] or 0
            dados_mensais[mes['nome']]['saidas_nao_operacionais'] = float(total_saidas_nao_op)
            print(f"Saídas não operacionais para {mes['nome']}: {total_saidas_nao_op}")
        except Exception as e:
            print(f"Erro ao processar saídas não operacionais: {str(e)}")
    
    # Calcular fluxo líquido e saldo acumulado para cada mês
    saldo_anterior = 0  # Inicializa o saldo anterior como zero
    
    for mes in meses:
        # Calcular entradas e saídas do mês
        entradas_mes = (
            dados_mensais[mes['nome']]['entradas_vendas'] +
            dados_mensais[mes['nome']]['entradas_abates'] +
            dados_mensais[mes['nome']]['entradas_nao_operacionais']
        )
        
        saidas_mes = (
            dados_mensais[mes['nome']]['saidas_custos_fixos'] +
            dados_mensais[mes['nome']]['saidas_custos_variaveis'] +
            dados_mensais[mes['nome']]['saidas_compra_animais'] +
            dados_mensais[mes['nome']]['saidas_investimentos'] +
            dados_mensais[mes['nome']]['saidas_outros_investimentos'] +
            dados_mensais[mes['nome']]['saidas_nao_operacionais']
        )
        
        # Adicionar totais calculados ao dicionário de dados mensais
        dados_mensais[mes['nome']]['entradas_total'] = entradas_mes
        dados_mensais[mes['nome']]['saidas_total'] = saidas_mes
        
        # Adicionar total de saídas operacionais
        dados_mensais[mes['nome']]['saidas_op'] = (
            dados_mensais[mes['nome']]['saidas_custos_fixos'] +
            dados_mensais[mes['nome']]['saidas_custos_variaveis']
        )
        
        # Adicionar total de entradas operacionais
        dados_mensais[mes['nome']]['entradas_op'] = (
            dados_mensais[mes['nome']]['entradas_vendas'] +
            dados_mensais[mes['nome']]['entradas_abates']
        )
        
        # Calcular fluxo líquido do mês
        fluxo_liquido_mes = entradas_mes - saidas_mes
        
        # Definir saldo inicial do mês como o saldo acumulado do mês anterior
        dados_mensais[mes['nome']]['saldo_inicial'] = saldo_anterior
        
        # Calcular saldo acumulado do mês
        saldo_acumulado_mes = dados_mensais[mes['nome']]['saldo_inicial'] + fluxo_liquido_mes
        
        dados_mensais[mes['nome']]['fluxo_liquido'] = fluxo_liquido_mes
        dados_mensais[mes['nome']]['saldo_acumulado'] = saldo_acumulado_mes
        
        # Atualizar o saldo anterior para o próximo mês
        saldo_anterior = saldo_acumulado_mes
        
        print(f"Fluxo líquido para o mês {mes['nome']}: {fluxo_liquido_mes}")
        print(f"Saldo acumulado para o mês {mes['nome']}: {saldo_acumulado_mes}")
    
    print("Processamento de dados concluído com sucesso")
    
    # Retornar dados processados
    return {
        'meses': meses,
        'dados_mensais': dados_mensais
    }
