from datetime import date, timedelta
from django.db.models import Sum, Count, F, Q, FloatField, DecimalField, Avg, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import Animal, Pesagem, RegistroMorte
from .models_abates import Abate, AbateAnimal
from django.db.models import OuterRef, Subquery

def get_estatisticas_animais(request, queryset=None):
    """
    Calcula estatísticas dos animais incluindo:
    - Contagem e peso por status
    - Variação anual
    - Distribuição por categoria
    """
    if queryset is None:
        queryset = Animal.objects.filter(usuario=request.user)

    # Data atual e um ano atrás para cálculo de variação
    hoje = date.today()
    um_ano_atras = hoje - timedelta(days=365)

    # Inicializar dicionário de estatísticas
    stats = {
        'ATIVO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00')},
        'VENDIDO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00')},
        'MORTO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00')},
        'ABATIDO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00')}
    }

    # Subconsulta para última pesagem
    ultima_pesagem = Pesagem.objects.filter(
        animal=OuterRef('pk')
    ).order_by('-data').values('peso')[:1]

    # Calcular estatísticas para cada status
    for status in ['ATIVO', 'VENDIDO', 'MORTO', 'ABATIDO']:
        # Contagem atual e peso total em uma única query
        stats_atuais = queryset.filter(situacao=status).aggregate(
            quantidade=Count('id'),
            peso_total=Coalesce(
                Sum(
                    Coalesce(
                        Subquery(ultima_pesagem, output_field=DecimalField(max_digits=10, decimal_places=2)),
                        F('peso_entrada')
                    )
                ),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        
        stats[status]['quantidade'] = stats_atuais['quantidade']
        stats[status]['peso_total'] = Decimal(str(stats_atuais['peso_total']))

        # Contagem do ano anterior em uma única query
        qtd_ano_anterior = Animal.objects.filter(
            usuario=request.user,
            situacao=status,
            data_cadastro__lte=um_ano_atras
        ).count()

        # Calcular variação percentual
        if qtd_ano_anterior > 0:
            variacao = ((stats[status]['quantidade'] - qtd_ano_anterior) / qtd_ano_anterior) * 100
        else:
            variacao = 100 if stats[status]['quantidade'] > 0 else 0
        stats[status]['variacao'] = round(variacao, 1)

        # Cálculo de arrobas baseado no status
        if status == 'ATIVO':
            # Para animais ativos, usar peso vivo/30
            stats[status]['peso_arroba'] = stats[status]['peso_total'] / Decimal('30.0')
        elif status == 'ABATIDO':
            # Para animais abatidos, usar peso vivo/30 (simplificado para performance)
            stats[status]['peso_arroba'] = stats[status]['peso_total'] / Decimal('30.0')
        else:
            # Para outros status (VENDIDO, MORTO), usar peso vivo/30
            stats[status]['peso_arroba'] = stats[status]['peso_total'] / Decimal('30.0')

    # Calcular distribuição por categoria em uma única query
    categorias = []
    for categoria in queryset.values('categoria_animal__nome').annotate(
        quantidade=Count('id')
    ).order_by('-quantidade'):
        categorias.append({
            'categoria_nome': categoria['categoria_animal__nome'] or 'Sem Categoria',
            'quantidade': categoria['quantidade']
        })

    return {
        'stats': stats,
        'categorias': categorias
    }

def get_estatisticas_detalhadas(request, queryset=None):
    from django.db.models import Count, Sum, Q
    
    # Se não receber um queryset, usa todos os animais do usuário
    if queryset is None:
        queryset = Animal.objects.filter(usuario=request.user)
    
    # Inicializa o dicionário com todos os status possíveis
    stats = {
        'ATIVO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'VENDIDO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'MORTO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'ABATIDO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0}
    }
    
    # Contagem atual
    contagem_atual = queryset.values('situacao').annotate(
        total=Count('id'),
        peso_total=Coalesce(Sum('peso_atual'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=10, decimal_places=2)),
        peso_arroba=Coalesce(
            Sum('peso_atual') / Value(Decimal('15.0')), 
            Value(Decimal('0.00')), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )
    
    # Preenche as quantidades atuais
    for item in contagem_atual:
        situacao = item['situacao']
        if situacao in stats:
            stats[situacao].update({
                'quantidade': item['total'],
                'peso_total': item['peso_total'] or Decimal('0.00'),
                'peso_arroba': item['peso_arroba'] or Decimal('0.00')
            })

    # Para animais ativos, calcula estimativa de carcaça com 50% rendimento
    for situacao in ['ATIVO']:
        if situacao in stats:
            peso_vivo = Decimal(str(stats[situacao]['peso_total']))
            rendimento = Decimal('0.50')  # 50% fixo para animais vivos
            peso_carcaca = peso_vivo * rendimento
            stats[situacao].update({
                'peso_carcaca': peso_carcaca,
                'peso_carcaca_arroba': peso_carcaca / Decimal('15.0'),
                'rendimento_medio': rendimento * Decimal('100.0')  # Converte para percentual
            })
    
    # Para animais mortos, busca informações detalhadas incluindo prejuízo
    animais_mortos = queryset.filter(situacao='MORTO')
    if animais_mortos.exists():
        # Buscar dados de morte em uma única query
        mortes_info = (
            RegistroMorte.objects
            .filter(animal__in=animais_mortos)
            .aggregate(
                prejuizo_total=Coalesce(Sum('prejuizo'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=10, decimal_places=2)),
            )
        )
        
        # Assume rendimento médio de 50% para cálculos
        peso_vivo = stats['MORTO']['peso_total']
        rendimento = Decimal('0.50')  # 50% fixo para animais mortos
        peso_carcaca = peso_vivo * rendimento
        
        stats['MORTO'].update({
            'peso_carcaca': peso_carcaca,
            'peso_carcaca_arroba': peso_carcaca / Decimal('15.0'),
            'rendimento_medio': rendimento * Decimal('100.0'),  # Converte para percentual
            'prejuizo_total': mortes_info['prejuizo_total']
        })

    # Para animais abatidos, busca informações detalhadas
    animais_abatidos = queryset.filter(situacao='ABATIDO')
    if animais_abatidos.exists():
        # Buscar dados de abate em uma única query
        abates_info = (
            AbateAnimal.objects
            .filter(animal__in=animais_abatidos)
            .select_related('abate')
            .aggregate(
                peso_vivo_total=Coalesce(Sum('peso_vivo'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=10, decimal_places=2)),
                rendimento_medio=Coalesce(
                    Avg('rendimento'), 
                    Value(Decimal('50.00')), 
                    output_field=DecimalField(max_digits=5, decimal_places=2)
                )
            )
        )

        peso_vivo = abates_info['peso_vivo_total']
        rendimento = Decimal(str(abates_info['rendimento_medio'])) / Decimal('100.0')  # Converte de percentual para decimal
        peso_carcaca = peso_vivo * rendimento

        stats['ABATIDO'].update({
            'peso_total': peso_vivo,
            'peso_arroba': peso_vivo / Decimal('15.0'),
            'peso_carcaca': peso_carcaca,
            'peso_carcaca_arroba': peso_carcaca / Decimal('15.0'),
            'rendimento_medio': rendimento * Decimal('100.0')  # Converte para percentual
        })
    
    return stats