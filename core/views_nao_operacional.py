from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F, Value, CharField
from datetime import datetime
from django.utils import timezone
from .models import MovimentacaoNaoOperacional, ContaBancaria, Fazenda
from .forms import MovimentacaoNaoOperacionalForm

@login_required
def lista_nao_operacional(request):
    # Filtros
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    tipo = request.GET.get('tipo', '')
    
    # Query base
    movimentacoes = MovimentacaoNaoOperacional.objects.filter(usuario=request.user).annotate(
        status_calculado=Case(
            When(data_pagamento__isnull=False, then=Value('PAGO')),
            When(data_vencimento__lt=timezone.now().date(), then=Value('VENCIDO')),
            default=Value('PENDENTE'),
            output_field=CharField(),
        )
    )
    
    # Aplicar filtros
    if search_query:
        movimentacoes = movimentacoes.filter(
            Q(observacoes__icontains=search_query) |
            Q(conta_bancaria__banco__icontains=search_query) |
            Q(fazenda__nome__icontains=search_query)
        )
    
    if status:
        if status == 'PAGO':
            movimentacoes = movimentacoes.filter(data_pagamento__isnull=False)
        elif status == 'VENCIDO':
            movimentacoes = movimentacoes.filter(data_vencimento__lt=timezone.now().date(), data_pagamento__isnull=True)
        elif status == 'PENDENTE':
            movimentacoes = movimentacoes.filter(data_vencimento__gte=timezone.now().date(), data_pagamento__isnull=True)
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    
    # Calcula os totais por status
    totais_status = movimentacoes.aggregate(
        total_pago=Sum(Case(
            When(data_pagamento__isnull=False, then='valor'),
            default=0,
            output_field=DecimalField()
        )),
        total_pendente=Sum(Case(
            When(data_pagamento__isnull=True, data_vencimento__gte=timezone.now().date(), then='valor'),
            default=0,
            output_field=DecimalField()
        )),
        total_vencido=Sum(Case(
            When(data_pagamento__isnull=True, data_vencimento__lt=timezone.now().date(), then='valor'),
            default=0,
            output_field=DecimalField()
        )),
        total_geral=Sum('valor'),
        count_pago=Count(Case(When(data_pagamento__isnull=False, then=1))),
        count_pendente=Count(Case(When(data_pagamento__isnull=True, data_vencimento__gte=timezone.now().date(), then=1))),
        count_vencido=Count(Case(When(data_pagamento__isnull=True, data_vencimento__lt=timezone.now().date(), then=1))),
    )
    
    context = {
        'movimentacoes': movimentacoes,
        'total_movimentacoes': movimentacoes.count(),
        'movimentacoes_pagas': totais_status['count_pago'],
        'movimentacoes_pendentes': totais_status['count_pendente'],
        'movimentacoes_vencidas': totais_status['count_vencido'],
        'valor_total_pago': totais_status['total_pago'] or 0,
        'valor_total_pendente': totais_status['total_pendente'] or 0,
        'valor_total_vencido': totais_status['total_vencido'] or 0,
        'valor_total_geral': totais_status['total_geral'] or 0,
        'search_query': search_query,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo': tipo,
        'today': timezone.now().date(),
    }
    return render(request, 'core/nao_operacional/lista.html', context)

@login_required
def criar_nao_operacional(request):
    if request.method == 'POST':
        form = MovimentacaoNaoOperacionalForm(request.POST, user=request.user)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            messages.success(request, 'Não operacional criado com sucesso!')
            return redirect('lista_nao_operacional')
    else:
        form = MovimentacaoNaoOperacionalForm(user=request.user)
    
    context = {
        'form': form,
        'titulo': 'Novo Não Operacional',
    }
    return render(request, 'core/nao_operacional/form.html', context)

@login_required
def editar_nao_operacional(request, pk):
    movimentacao = get_object_or_404(MovimentacaoNaoOperacional, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        form = MovimentacaoNaoOperacionalForm(request.POST, instance=movimentacao, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro não operacional atualizado com sucesso!')
            return redirect('lista_nao_operacional')
    else:
        form = MovimentacaoNaoOperacionalForm(instance=movimentacao, user=request.user)
    
    context = {
        'form': form,
        'titulo': 'Editar Não Operacional',
    }
    return render(request, 'core/nao_operacional/form.html', context)

@login_required
def excluir_nao_operacional(request, pk):
    movimentacao = get_object_or_404(MovimentacaoNaoOperacional, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Não operacional excluído com sucesso!')
        return redirect('lista_nao_operacional')
    
    context = {
        'object': movimentacao,
        'titulo': 'Excluir Não Operacional',
    }
    return render(request, 'core/nao_operacional/excluir.html', context)
