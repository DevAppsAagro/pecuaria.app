from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, F, Q, Case, When, Value, IntegerField, FloatField
from django.db.models.functions import Coalesce

from .models import Animal, Lote, Fazenda
from .models_reproducao import EstacaoMonta, ManejoReproducao

@login_required
def relatorio_reprodutivo(request):
    """
    Relatório de reprodução mostrando métricas de fertilidade, nascimento, desmame, etc.
    """
    # Obter todas as estações de monta do usuário
    estacoes = EstacaoMonta.objects.filter(fazenda__usuario=request.user).order_by('-data_inicio')
    
    # Filtros
    estacao_id = request.GET.get('estacao_id')
    lote_id = request.GET.get('lote_id')
    
    # Lotes disponíveis para seleção
    if estacao_id:
        # Se uma estação foi selecionada, mostrar apenas lotes relacionados a essa estação
        try:
            estacao = EstacaoMonta.objects.get(id=estacao_id, fazenda__usuario=request.user)
            lotes = estacao.lotes.all().order_by('id_lote')
        except EstacaoMonta.DoesNotExist:
            lotes = []
    else:
        # Se nenhuma estação foi selecionada, não mostrar nenhum lote
        lotes = []
    
    # Dados do relatório
    dados_relatorio = {}
    
    if estacao_id:
        estacao = EstacaoMonta.objects.get(id=estacao_id, fazenda__usuario=request.user)
        
        # Filtrar por lote se especificado
        filtro_base = Q(estacao_monta=estacao)
        if lote_id:
            filtro_base &= Q(lote_id=lote_id)
        
        # Consulta base para manejo reprodutivo
        qs_manejo = ManejoReproducao.objects.filter(filtro_base)
        
        # Total de animais em cobertura (todos os animais do lote na estação de monta)
        total_cobertura = qs_manejo.count()  # Contando todos os animais no manejo reprodutivo
        
        # Total de animais prenhe
        total_prenhe = qs_manejo.filter(diagnostico='PRENHE').count()
        
        # Total de nascimentos
        total_nascimentos = qs_manejo.filter(resultado='NASCIMENTO').count()
        
        # Total de desmames (assumindo que desmame é contabilizado em outro lugar)
        # Essa informação pode precisar ser calculada com base em outros dados
        total_desmames = 0  # Placeholder
        
        # Doses de sêmen gastas (placeholder - ajustar conforme necessário)
        doses_semen = total_cobertura  # Assumindo 1 dose por cobertura
        
        # Cálculo dos índices
        if total_cobertura > 0:
            indice_fertilidade = (total_prenhe / total_cobertura) * 100
        else:
            indice_fertilidade = 0
            
        if total_prenhe > 0:
            indice_servico = doses_semen / total_prenhe
        else:
            indice_servico = 0
            
        if total_prenhe > 0:
            perda_preparto = ((total_prenhe - total_nascimentos) / total_prenhe) * 100 if total_prenhe > 0 else 0
        else:
            perda_preparto = 0
            
        # Placeholders para valores que precisam ser calculados com base em outros dados
        mortalidade_bezerros = 0
        perda_predesmame = 0
        taxa_desmame = (total_desmames / total_prenhe) * 100 if total_prenhe > 0 else 0
        relacao_desmame = (total_desmames / total_cobertura) * 100 if total_cobertura > 0 else 0
        
        peso_medio_desmame_machos = 0  # Placeholder
        peso_medio_desmame_femeas = 0  # Placeholder
        quilos_desmamados_vaca = 0  # Placeholder
        
        # Nome do lote da estação
        lote_estacao = ", ".join([l.id_lote for l in estacao.lotes.all()])
        
        # Nome do lote de nascimentos (assumindo que é o mesmo da estação)
        lote_nascimentos = lote_estacao
        
        dados_relatorio = {
            'lote_estacao': lote_estacao,
            'lote_nascimentos': lote_nascimentos,
            'total_cobertura': total_cobertura,
            'total_prenhe': total_prenhe,
            'total_nascimentos': total_nascimentos,
            'total_desmames': total_desmames,
            'doses_semen': doses_semen,
            'indice_fertilidade': round(indice_fertilidade, 2),
            'indice_servico': round(indice_servico, 2),
            'perda_preparto': round(perda_preparto, 2),
            'mortalidade_bezerros': mortalidade_bezerros,
            'perda_predesmame': perda_predesmame,
            'taxa_desmame': round(taxa_desmame, 2),
            'relacao_desmame': round(relacao_desmame, 2),
            'peso_medio_desmame_machos': peso_medio_desmame_machos,
            'peso_medio_desmame_femeas': peso_medio_desmame_femeas,
            'quilos_desmamados_vaca': quilos_desmamados_vaca,
        }
        
        # Dados para os gráficos
        # Gráfico de Resultados
        dados_grafico_resultados = {
            'labels': ['Total em cobertura', 'Total de Prenhes', 'Total de Nascimentos', 'Total de Desmames', 'Doses de Sêmen gastas'],
            'values': [total_cobertura, total_prenhe, total_nascimentos, total_desmames, doses_semen],
            'colors': ['rgba(54, 162, 235, 0.5)', 'rgba(75, 192, 192, 0.5)', 'rgba(255, 206, 86, 0.5)', 'rgba(255, 99, 132, 0.5)', 'rgba(153, 102, 255, 0.5)'],
            'borders': ['rgba(54, 162, 235, 1)', 'rgba(75, 192, 192, 1)', 'rgba(255, 206, 86, 1)', 'rgba(255, 99, 132, 1)', 'rgba(153, 102, 255, 1)']
        }
        
        # Gráfico de Indicadores Zootécnicos
        dados_grafico_indicadores = {
            'labels': ['Índice de Fertilidade', 'Perda Pré-parto', 'Mortalidade de Bezerros', 'Perda pré-desmame', 'Taxa de Desmame', 'Relação de Desmame'],
            'values': [indice_fertilidade, perda_preparto, mortalidade_bezerros, perda_predesmame, taxa_desmame, relacao_desmame],
            'colors': ['rgba(54, 162, 235, 0.5)', 'rgba(255, 99, 132, 0.5)', 'rgba(255, 159, 64, 0.5)', 'rgba(255, 205, 86, 0.5)', 'rgba(75, 192, 192, 0.5)', 'rgba(153, 102, 255, 0.5)'],
            'borders': ['rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)', 'rgba(255, 159, 64, 1)', 'rgba(255, 205, 86, 1)', 'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)']
        }
        
    else:
        dados_relatorio = {}
        dados_grafico_resultados = {
            'labels': [],
            'values': [],
            'colors': [],
            'borders': []
        }
        dados_grafico_indicadores = {
            'labels': [],
            'values': [],
            'colors': [],
            'borders': []
        }
    
    context = {
        'estacoes': estacoes,
        'lotes': lotes,
        'filtros': {
            'estacao_id': estacao_id,
            'lote_id': lote_id,
        },
        'dados_relatorio': dados_relatorio,
        'dados_grafico_resultados': dados_grafico_resultados,
        'dados_grafico_indicadores': dados_grafico_indicadores,
    }
    
    return render(request, 'Relatorios/relatorio_reprodutivo.html', context)
