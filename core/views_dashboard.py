import json
from datetime import datetime, date, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q

from .models import Fazenda
from .views_relatorios import atualizar_dre_dados

@login_required
def dashboard(request):
    """
    View principal para o dashboard financeiro
    """
    # Obtém as fazendas do usuário para o filtro
    fazendas = Fazenda.objects.filter(usuario=request.user).order_by('nome')
    
    # Contexto para o template
    context = {
        'fazendas': fazendas,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def dashboard_dados(request):
    """
    API para fornecer dados para o dashboard
    """
    try:
        # Parâmetros do filtro
        fazenda = request.GET.get('fazenda')
        data_inicial_str = request.GET.get('data_inicial')
        data_final_str = request.GET.get('data_final')
        
        print(f"Período: {data_inicial_str} a {data_final_str}")
        
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
        
        # Obter dados financeiros usando a função já existente do DRE
        dados_dre = atualizar_dre_dados(request.user, data_inicial, data_final, fazenda)
        
        # Adicionar dados adicionais específicos para o dashboard aqui
        # Por exemplo, dados históricos para gráficos de evolução
        
        # Preparar dados para o gráfico de receitas vs despesas (6 meses)
        dados_historicos = obter_dados_historicos(request.user, data_final, fazenda)
        dados_dre['dados_historicos'] = dados_historicos
        
        # Adicionar campo de sucesso para a API
        dados_dre['success'] = True
        
        return JsonResponse(dados_dre)
            
    except Exception as e:
        import traceback
        print(f"Erro ao processar dados do dashboard: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def obter_dados_historicos(usuario, data_final, fazenda=None):
    """
    Obtém dados históricos para os últimos 6 meses para o gráfico de evolução
    """
    # Conversão para date em caso de datetime
    if isinstance(data_final, datetime):
        data_final = data_final.date()
    
    # Inicializa estrutura de dados
    dados_historicos = {
        'meses': [],
        'receitas': [],
        'despesas': [],
        'resultados': []
    }
    
    # Obter dados mês a mês para os últimos 6 meses
    for i in range(5, -1, -1):
        # Calcula mês de referência (voltando i meses a partir da data final)
        ultimo_dia = data_final.replace(day=1)
        for _ in range(i):
            # Cálculo seguro para voltar um mês (considerando meses com diferentes números de dias)
            ultimo_dia = (ultimo_dia - timedelta(days=1)).replace(day=1)
        
        primeiro_dia = ultimo_dia
        ultimo_dia = (date(primeiro_dia.year + (1 if primeiro_dia.month == 12 else 0), 
                      (primeiro_dia.month % 12) + 1, 1) - timedelta(days=1))
        
        # Obter dados do mês
        dados_mes = atualizar_dre_dados(usuario, primeiro_dia, ultimo_dia, fazenda)
        
        # Nome do mês para o gráfico
        nome_mes = primeiro_dia.strftime('%b/%y')
        
        # Adicionar à estrutura de dados
        dados_historicos['meses'].append(nome_mes)
        dados_historicos['receitas'].append(float(dados_mes.get('receitas_totais', 0)))
        dados_historicos['despesas'].append(float(dados_mes.get('total_geral_custos', 0)))
        dados_historicos['resultados'].append(float(dados_mes.get('resultado_operacional', 0)))
    
    return dados_historicos
