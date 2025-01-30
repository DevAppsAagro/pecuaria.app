from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import datetime, timedelta

@login_required
def dashboard(request):
    """
    Dashboard principal com indicadores completos
    """
    context = {
        'fazendas': [
            {'id': 1, 'nome': 'Fazenda 1'},
            {'id': 2, 'nome': 'Fazenda 2'}
        ],
        'indicadores': {
            'producao': {
                'arrobas_totais': 1500,
                'arrobas_ha_ano': 12.5,
                'peso_vivo_total': 45000,
                'gmd_global': 0.850,
                'taxa_venda': 35,
                'taxa_desfrute': 42,
                'peso_desmame_machos': 240,
                'peso_desmame_femeas': 220,
                'quilos_desmamados': 180,
                'idade_abate': 24,
                'tempo_permanencia': 18,
                'peso_entrada_conf': 380,
                'peso_saida_conf': 540,
                'peso_morto_saida': 285,
                'ganho_carcaca': 52,
                'rendimento_ganho': 54
            },
            'financeiro': {
                'valor_arroba': 285.50,
                'desembolso_boi': 2800,
                'resultado_boi': 450,
                'desembolso_arroba': 180,
                'resultado_arroba': 105,
                'margem_venda': 28,
                'roi': 15,
                'receita_total': 850000,
                'despesas_total': 650000,
                'reposicao': 250000,
                'resultado_caixa': 200000,
                'variacao_insumos': 8.5,
                'resultado_final': 180000,
                'resultado_ha': 1200,
                'desembolso_cab': 85,
                'participacao_insumos': 65,
                'valor_medio_venda': 4200,
                'perc_desembolso': 75,
                'valor_diaria': 12.50,
                'desembolso_conf': 950
            },
            'reproducao': {
                'total_cobertura': 1200,
                'total_prenhes': 960,
                'fertilidade': 82,
                'indice_servico': 1.8,
                'nascimentos': 920,
                'doses_semen': 1500,
                'matrizes_prenhes': 850,
                'perda_pre_parto': 4.2,
                'mortalidade_bezerros': 3.8,
                'perda_pre_desmame': 2.5,
                'taxa_desmame': 78,
                'relacao_desmame': 0.85
            },
            'confinamento': {
                'gmd': 1.450,
                'ganho_carcaca': 58,
                'rendimento': 54,
                'valor_diaria': 12.50
            }
        },
        'dados_graficos': {
            'evolucao_peso': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'data': [380, 420, 460, 490, 520, 540]
            },
            'evolucao_gmd': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'data': [0.8, 0.85, 0.95, 0.92, 0.88, 0.90]
            },
            'gmd_lotes': {
                'labels': ['Lote 1', 'Lote 2', 'Lote 3', 'Lote 4', 'Lote 5'],
                'data': [0.95, 0.87, 0.92, 0.85, 0.89]
            },
            'evolucao_rebanho': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'data': [1200, 1180, 1220, 1250, 1180, 1150]
            },
            'taxa_prenhez': {
                'labels': ['IATF 1', 'Repasse 1', 'IATF 2', 'Repasse 2', 'Touro'],
                'data': [55, 15, 45, 12, 8],
                'meta': 85
            },
            'mortalidade': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'data': [2.1, 1.8, 2.2, 1.9, 2.0, 1.7]
            },
            'distribuicao_categorias': {
                'labels': ['Bezerros', 'Novilhas', 'Bois', 'Vacas'],
                'data': [25, 20, 30, 25]
            },
            'distribuicao_custos': {
                'labels': ['Nutrição', 'Saúde', 'Mão de obra', 'Pastagem', 'Outros'],
                'data': [45, 15, 20, 12, 8]
            },
            'evolucao_roi': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'data': [12, 13, 15, 14.5, 15.2, 14.8]
            },
            'indicadores_desmame': {
                'labels': ['Machos', 'Fêmeas'],
                'pesos': [240, 220],
                'metas': [250, 230]
            },
            'perdas_reproducao': {
                'labels': ['Pré-parto', 'Bezerros', 'Pré-desmame'],
                'data': [4.2, 3.8, 2.5]
            },
            'desempenho_confinamento': {
                'labels': ['Entrada', 'Saída', 'Peso Morto'],
                'data': [380, 540, 285]
            },
            'custos_operacionais': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'receitas': [140000, 145000, 150000, 148000, 152000, 155000],
                'despesas': [110000, 108000, 115000, 112000, 118000, 120000]
            },
            'eficiencia_reprodutiva': {
                'labels': ['Taxa Prenhez', 'Taxa Nascimento', 'Taxa Desmame'],
                'data': [82, 78, 75],
                'metas': [85, 80, 78]
            }
        }
    }
    return render(request, 'dashboard.html', context)

@login_required
def atualizar_dashboard(request):
    """
    Endpoint para atualizar os dados do dashboard via AJAX
    """
    fazenda_id = request.GET.get('fazenda')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    # Aqui virão os cálculos reais baseados nos filtros
    # Por enquanto retornamos dados fictícios
    data = {
        'success': True,
        'indicadores': {
            'producao': {
                'arrobas_totais': 1250,
                'gmd_global': 0.850,
                'taxa_venda': 35.5,
                'taxa_desfrute': 28.3
            },
            # ... outros indicadores ...
        }
    }
    
    return JsonResponse(data)
