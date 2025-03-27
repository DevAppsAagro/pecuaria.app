"""
Versão otimizada da função animal_list para melhorar o desempenho da listagem de animais.
Para usar, substitua a função animal_list em views.py por esta versão.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Max, F, OuterRef, Subquery, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import Coalesce
from .models import Animal, Pesagem, CategoriaAnimal, Raca, Lote, Pasto, Fazenda
from .views_estatisticas import get_estatisticas_animais, get_estatisticas_detalhadas

@login_required
def animal_list_optimized(request):
    """
    Versão otimizada da função animal_list para melhorar o desempenho.
    """
    # Cache as consultas comuns
    user = request.user
    
    # Otimiza a subconsulta do peso mais recente
    ultima_pesagem = (
        Pesagem.objects
        .filter(animal=OuterRef('pk'))
        .order_by('-data')
        .values('peso')[:1]
    )
    
    # Query base otimizada com select_related e prefetch_related
    queryset = (
        Animal.objects
        .filter(usuario=user)
        .select_related(
            'raca',
            'lote',
            'categoria_animal',
            'fazenda_atual',
            'pasto_atual'
        )
        .annotate(
            peso_atual=Coalesce(
                Subquery(ultima_pesagem),
                F('peso_entrada')
            )
        )
        .only(  # Seleciona apenas os campos necessários
            'id',
            'brinco_visual',
            'brinco_eletronico',
            'data_nascimento',
            'situacao',
            'peso_entrada',
            'raca__nome',
            'lote__id_lote',
            'categoria_animal__nome',
            'fazenda_atual__nome',
            'pasto_atual__id_pasto',
            'pasto_atual__nome'
        )
        .defer('observacoes')  # Exclui campos grandes não utilizados
    )
    
    # Cache das opções de filtro - usando valores em vez de objetos para reduzir overhead
    categorias = (
        CategoriaAnimal.objects
        .filter(Q(usuario=None) | Q(usuario=user))
        .only('id', 'nome', 'sexo')
        .order_by('nome')
        .values('id', 'nome', 'sexo')
    )
    
    racas = (
        Raca.objects
        .filter(Q(usuario=None) | Q(usuario=user))
        .only('id', 'nome')
        .order_by('nome')
        .values('id', 'nome')
    )
    
    # Filtros otimizados
    filtros = {}
    
    if request.GET.get('fazenda'):
        filtros['fazenda'] = request.GET.get('fazenda')
        queryset = queryset.filter(fazenda_atual_id=filtros['fazenda'])
        
        # Cache dos lotes e pastos filtrados - usando valores
        lotes = (
            Lote.objects
            .filter(fazenda_id=filtros['fazenda'], usuario=user)
            .only('id', 'id_lote')
            .values('id', 'id_lote')
        )
        pastos = (
            Pasto.objects
            .filter(fazenda_id=filtros['fazenda'], fazenda__usuario=user)
            .only('id', 'id_pasto', 'nome')
            .values('id', 'id_pasto', 'nome')
        )
    else:
        lotes = (
            Lote.objects
            .filter(usuario=user)
            .only('id', 'id_lote')
            .values('id', 'id_lote')
        )
        pastos = (
            Pasto.objects
            .filter(fazenda__usuario=user)
            .only('id', 'id_pasto', 'nome')
            .values('id', 'id_pasto', 'nome')
        )
    
    # Aplicar outros filtros
    if request.GET.get('lote'):
        filtros['lote'] = request.GET.get('lote')
        queryset = queryset.filter(lote_id=filtros['lote'])
    
    if request.GET.get('pasto'):
        filtros['pasto'] = request.GET.get('pasto')
        queryset = queryset.filter(pasto_atual_id=filtros['pasto'])
    
    if request.GET.get('categoria'):
        categoria_id = request.GET.get('categoria')
        filtros['categoria'] = int(categoria_id)
        queryset = queryset.filter(categoria_animal_id=filtros['categoria'])
    
    if request.GET.get('raca'):
        raca_id = request.GET.get('raca')
        filtros['raca'] = int(raca_id)
        queryset = queryset.filter(raca_id=filtros['raca'])
    
    if request.GET.get('brinco'):
        filtros['brinco'] = request.GET.get('brinco')
        queryset = queryset.filter(
            Q(brinco_visual__icontains=filtros['brinco']) |
            Q(brinco_eletronico__icontains=filtros['brinco'])
        )

    # Obtém as estatísticas usando queryset otimizado
    estatisticas = get_estatisticas_animais(request, queryset)
    
    # Obtém estatísticas detalhadas apenas se necessário
    estatisticas_detalhadas = get_estatisticas_detalhadas(request, queryset)

    # Paginação com tamanho aumentado para corresponder ao DataTables
    items_per_page = 100  # Aumentado para reduzir requisições de paginação
    paginator = Paginator(queryset, items_per_page)
    page = request.GET.get('page')
    
    try:
        animais_paginados = paginator.page(page)
    except PageNotAnInteger:
        animais_paginados = paginator.page(1)
    except EmptyPage:
        animais_paginados = paginator.page(paginator.num_pages)

    # Cache da query de fazendas
    fazendas = (
        Fazenda.objects
        .filter(usuario=user)
        .only('id', 'nome')
        .values('id', 'nome')
    )

    context = {
        'animais': animais_paginados,
        'fazendas': fazendas,
        'lotes': lotes,
        'pastos': pastos,
        'categorias': categorias,
        'racas': racas,
        'filtros': filtros,
        'estatisticas': estatisticas,
        'estatisticas_detalhadas': estatisticas_detalhadas,
        'categorias_chart': estatisticas['categorias'],
        'total_ativos': estatisticas['stats']['ATIVO']['quantidade'],
        'total_vendidos': estatisticas['stats']['VENDIDO']['quantidade'],
        'total_mortos': estatisticas['stats']['MORTO']['quantidade'],
        'total_abatidos': estatisticas['stats']['ABATIDO']['quantidade'],
        'total_peso_kg': estatisticas['stats']['ATIVO']['peso_total'],
        'total_peso_arroba': estatisticas['stats']['ATIVO']['peso_arroba'],
        'active_tab': 'animais'
    }
    
    return render(request, 'animais/animal_list.html', context)
