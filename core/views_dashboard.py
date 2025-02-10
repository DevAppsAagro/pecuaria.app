from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
from .models import Fazenda, Pasto, Benfeitoria, Animal, Despesa, ExtratoBancario
from datetime import datetime, timedelta

@login_required
def dashboard(request):
    """View para o dashboard principal"""
    # Obtém as fazendas do usuário
    fazendas = Fazenda.objects.filter(usuario=request.user)
    primeira_fazenda = fazendas.first()
    
    # Filtra por fazenda se especificado
    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        fazenda_filter = {'id': fazenda_id}
        animal_filter = {'fazenda_atual_id': fazenda_id}
        despesa_filter = {'itens__fazenda_destino_id': fazenda_id, 'usuario': request.user}
        extrato_filter = {'conta__fazenda_id': fazenda_id, 'usuario': request.user}
    else:
        fazenda_filter = {'usuario': request.user}
        animal_filter = {'fazenda_atual__usuario': request.user}
        despesa_filter = {'usuario': request.user}
        extrato_filter = {'usuario': request.user}
    
    # Estatísticas gerais
    total_fazendas = fazendas.count()
    total_pastos = Pasto.objects.filter(fazenda__usuario=request.user).count()
    total_benfeitorias = Benfeitoria.objects.filter(fazenda__usuario=request.user).count()
    
    # Calcula área total dos pastos
    total_area_pastos = Pasto.objects.filter(
        fazenda__usuario=request.user
    ).aggregate(total_area=Sum('area'))['total_area'] or 0
    
    # Dados para os gráficos
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Despesas do mês - soma valor_total dos itens + multa_juros - desconto
    despesas_mes = Despesa.objects.filter(
        **despesa_filter,
        data_vencimento__range=[inicio_mes, fim_mes]
    ).annotate(
        total_itens=Coalesce(Sum('itens__valor_total'), 0, output_field=DecimalField()),
        valor_total=F('total_itens') + F('multa_juros') - F('desconto')
    ).distinct().aggregate(
        total=Sum('valor_total')
    )['total'] or 0
    
    # Receitas do mês (soma de vendas e abates)
    receitas_mes = ExtratoBancario.objects.filter(
        Q(tipo='venda') | Q(tipo='abate'),
        data__range=[inicio_mes, fim_mes],
        **extrato_filter
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Se o valor for negativo (por causa do sinal), converte para positivo
    receitas_mes = abs(receitas_mes)
    
    # Contagem de animais por categoria
    animais_por_categoria = Animal.objects.filter(
        **animal_filter
    ).values('categoria_animal__nome').annotate(
        total=Count('id')
    ).order_by('categoria_animal__nome')
    
    context = {
        'fazendas': fazendas,
        'primeira_fazenda': primeira_fazenda,
        'total_fazendas': total_fazendas,
        'total_pastos': total_pastos,
        'total_benfeitorias': total_benfeitorias,
        'total_area_pastos': round(total_area_pastos, 2),
        'despesas_mes': despesas_mes,
        'receitas_mes': receitas_mes,
        'animais_por_categoria': animais_por_categoria,
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
    
    # Filtra por fazenda se especificado
    if fazenda_id:
        despesa_filter = {'itens__fazenda_destino_id': fazenda_id, 'usuario': request.user}
        extrato_filter = {'conta__fazenda_id': fazenda_id, 'usuario': request.user}
    else:
        despesa_filter = {'usuario': request.user}
        extrato_filter = {'usuario': request.user}
    
    # Calcula os indicadores baseados nos filtros
    hoje = datetime.now().date()
    inicio_mes = data_inicio if data_inicio else hoje.replace(day=1)
    fim_mes = data_fim if data_fim else (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Despesas do período - soma valor_total dos itens + multa_juros - desconto
    despesas = Despesa.objects.filter(
        **despesa_filter,
        data_vencimento__range=[inicio_mes, fim_mes]
    ).annotate(
        total_itens=Coalesce(Sum('itens__valor_total'), 0, output_field=DecimalField()),
        valor_total=F('total_itens') + F('multa_juros') - F('desconto')
    ).distinct().aggregate(
        total=Sum('valor_total')
    )['total'] or 0
    
    # Receitas do período (soma de vendas e abates)
    receitas = ExtratoBancario.objects.filter(
        Q(tipo='venda') | Q(tipo='abate'),
        data__range=[inicio_mes, fim_mes],
        **extrato_filter
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Se o valor for negativo (por causa do sinal), converte para positivo
    receitas = abs(receitas)
    
    data = {
        'success': True,
        'indicadores': {
            'despesas': round(despesas, 2),
            'receitas': round(receitas, 2),
            'resultado': round(receitas - despesas, 2)
        }
    }
    
    return JsonResponse(data)
