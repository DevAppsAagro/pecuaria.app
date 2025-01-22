from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from .models import MovimentacaoNaoOperacional, ContaBancaria, Fazenda
from .forms import MovimentacaoNaoOperacionalForm

@login_required
def lista_nao_operacional(request):
    search_query = request.GET.get('search', '')
    movimentacoes = MovimentacaoNaoOperacional.objects.filter(usuario=request.user)
    
    if search_query:
        movimentacoes = movimentacoes.filter(
            Q(observacoes__icontains=search_query) |
            Q(conta_bancaria__nome__icontains=search_query) |
            Q(fazenda__nome__icontains=search_query)
        )
    
    paginator = Paginator(movimentacoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
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
