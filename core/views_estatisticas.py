from datetime import date, timedelta
from django.db.models import Sum, Count, F, Q, FloatField
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import Animal, Pesagem
from .models_abates import Abate, AbateAnimal

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

    # Inicializar dicionário de estatísticas com dados fictícios para mortos
    stats = {
        'ATIVO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00'), 'peso_carcaca': Decimal('0.00'), 'peso_carcaca_arroba': Decimal('0.00')},
        'VENDIDO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00')},
        'MORTO': {'quantidade': 2, 'variacao': -50, 'peso_total': Decimal('800.00'), 'peso_arroba': Decimal('53.33')},  # Dados fictícios
        'ABATIDO': {'quantidade': 0, 'variacao': 0, 'peso_total': Decimal('0.00'), 'peso_arroba': Decimal('0.00'), 'peso_carcaca': Decimal('0.00'), 'peso_carcaca_arroba': Decimal('0.00')}
    }

    # Calcular estatísticas para cada status (exceto MORTO que já tem dados fictícios)
    for status in ['ATIVO', 'VENDIDO', 'ABATIDO']:
        # Contagem atual
        animais_status = queryset.filter(situacao=status)
        stats[status]['quantidade'] = animais_status.count()

        # Contagem do ano anterior para cálculo de variação
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

        # Calcular peso total usando subquery para última pesagem
        peso_total = Decimal('0.00')
        for animal in animais_status:
            ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
            peso = ultima_pesagem.peso if ultima_pesagem else animal.peso_entrada
            if peso:
                peso_total += Decimal(str(peso))
        
        stats[status]['peso_total'] = peso_total

        # Cálculo de arrobas baseado no status
        if status == 'ATIVO':
            # Para animais ativos, usar 50% de rendimento (peso_vivo/30)
            stats[status]['peso_arroba'] = peso_total / Decimal('30.0') if peso_total > 0 else Decimal('0.00')
        elif status == 'ABATIDO':
            # Para animais abatidos, usar o rendimento real do abate
            peso_arroba = Decimal('0.00')
            for animal in animais_status:
                ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
                peso = ultima_pesagem.peso if ultima_pesagem else animal.peso_entrada
                if peso:
                    # Buscar o rendimento do abate através do AbateAnimal
                    abate_animal = AbateAnimal.objects.filter(
                        animal=animal
                    ).select_related('abate').first()
                    
                    if abate_animal and abate_animal.rendimento:
                        rendimento = Decimal(str(abate_animal.rendimento)) / Decimal('100.0')
                        peso_arroba += (Decimal(str(peso)) * rendimento) / Decimal('15.0')
                    else:
                        # Se não tiver rendimento registrado, usar 50%
                        peso_arroba += Decimal(str(peso)) / Decimal('30.0')
            stats[status]['peso_arroba'] = peso_arroba
        else:
            # Para outros status (VENDIDO, MORTO), usar peso vivo/30
            stats[status]['peso_arroba'] = peso_total / Decimal('30.0') if peso_total > 0 else Decimal('0.00')

        # Calcular peso de carcaça (50% do peso vivo) para animais ativos e abatidos
        if status in ['ATIVO', 'ABATIDO']:
            stats[status]['peso_carcaca'] = peso_total * Decimal('0.50')
            stats[status]['peso_carcaca_arroba'] = stats[status]['peso_carcaca'] / Decimal('15.0')

    # Calcular distribuição por categoria
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
