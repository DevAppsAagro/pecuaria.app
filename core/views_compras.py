from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Animal, Contato, ContaBancaria
from .models_compras import Compra, CompraAnimal
from .models_parcelas import ParcelaCompra
from .forms_compras import CompraForm

@login_required
def compras_list(request):
    search_query = request.GET.get('search', '')
    
    compras = Compra.objects.filter(usuario=request.user)
    
    if search_query:
        compras = compras.filter(
            Q(animais__animal__brinco_visual__icontains=search_query) |
            Q(vendedor__nome__icontains=search_query)
        ).distinct()
    
    paginator = Paginator(compras, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query
    }
    
    return render(request, 'core/compras/lista.html', context)

def criar_parcelas(compra, valor_total):
    """Cria as parcelas para uma compra"""
    # Exclui parcelas existentes se houver
    ParcelaCompra.objects.filter(compra=compra).delete()
    
    # Se a compra já foi paga, cria apenas uma parcela paga
    if compra.data_pagamento:
        ParcelaCompra.objects.create(
            compra=compra,
            numero=1,
            valor=valor_total,
            data_vencimento=compra.data_vencimento,
            status='PAGO'
        )
        return
    
    # Calcula o valor de cada parcela
    valor_parcela = Decimal(valor_total) / Decimal(compra.numero_parcelas)
    valor_parcela = valor_parcela.quantize(Decimal('.01'))  # Arredonda para 2 casas decimais
    
    # Ajusta o valor da última parcela para compensar arredondamentos
    valor_ultima = valor_total - (valor_parcela * (compra.numero_parcelas - 1))
    
    # Cria as parcelas
    for i in range(compra.numero_parcelas):
        data_vencimento = compra.data_vencimento + timedelta(days=i * compra.intervalo_parcelas)
        valor = valor_ultima if i == compra.numero_parcelas - 1 else valor_parcela
        
        ParcelaCompra.objects.create(
            compra=compra,
            numero=i + 1,
            valor=valor,
            data_vencimento=data_vencimento,
            status='PENDENTE'
        )

@login_required
def criar_compra(request):
    # Filtra apenas animais ativos sem valor de compra
    animais_disponiveis = Animal.objects.filter(
        usuario=request.user,
        situacao='ATIVO',
        valor_compra__isnull=True
    )
    
    # Filtra apenas contatos do tipo fornecedor
    fornecedores = Contato.objects.filter(
        usuario=request.user,
        tipo='FO'
    )
    
    # Filtra contas bancárias ativas
    contas = ContaBancaria.objects.filter(
        usuario=request.user,
        ativa=True
    )
    
    if request.method == 'POST':
        form = CompraForm(request.POST, user=request.user)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.usuario = request.user
            compra.save()

            # Processa os animais selecionados
            animais_ids = request.POST.getlist('animal')
            if not animais_ids:
                messages.error(request, 'Selecione pelo menos um animal.')
                return render(request, 'core/compras/form.html', {'form': form})

            valor_total = Decimal('0')
            for animal_id in animais_ids:
                animal = Animal.objects.get(id=animal_id)
                valor = (Decimal(str(animal.peso_entrada)) * compra.valor_unitario 
                        if compra.tipo_compra == 'KG' 
                        else compra.valor_unitario)
                
                CompraAnimal.objects.create(
                    compra=compra,
                    animal=animal,
                    valor_total=valor
                )
                valor_total += valor
            
            # Cria as parcelas
            criar_parcelas(compra, valor_total)

            messages.success(request, 'Compra criada com sucesso!')
            return redirect('compras_list')
    else:
        form = CompraForm(user=request.user)
    
    context = {
        'form': form,
        'animais_disponiveis': animais_disponiveis,
        'fornecedores': fornecedores,
        'contas': contas
    }
    
    return render(request, 'core/compras/form.html', context)

@login_required
def editar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk, usuario=request.user)
    animais_compra = CompraAnimal.objects.filter(compra=compra)
    
    if request.method == 'POST':
        form = CompraForm(request.POST, instance=compra, user=request.user)
        if form.is_valid():
            compra = form.save()

            # Processa os animais selecionados
            animais_ids = request.POST.getlist('animal')
            if not animais_ids:
                messages.error(request, 'Selecione pelo menos um animal.')
                return render(request, 'core/compras/form.html', {'form': form})

            # Remove animais não selecionados
            CompraAnimal.objects.filter(compra=compra).exclude(animal_id__in=animais_ids).delete()

            # Atualiza ou cria novos animais
            valor_total = Decimal('0')
            for animal_id in animais_ids:
                animal = Animal.objects.get(id=animal_id)
                valor = (Decimal(str(animal.peso_entrada)) * compra.valor_unitario 
                        if compra.tipo_compra == 'KG' 
                        else compra.valor_unitario)
                
                CompraAnimal.objects.update_or_create(
                    compra=compra,
                    animal=animal,
                    defaults={'valor_total': valor}
                )
                valor_total += valor
            
            # Atualiza as parcelas
            criar_parcelas(compra, valor_total)

            messages.success(request, 'Compra atualizada com sucesso!')
            return redirect('compras_list')
    else:
        form = CompraForm(instance=compra, user=request.user)
    
    # Filtra animais disponíveis incluindo os já selecionados
    animais_disponiveis = Animal.objects.filter(
        Q(usuario=request.user, situacao='ATIVO', valor_compra__isnull=True) |
        Q(id__in=animais_compra.values_list('animal_id', flat=True))
    )
    
    context = {
        'form': form,
        'compra': compra,
        'animais_disponiveis': animais_disponiveis,
        'animais_selecionados': list(animais_compra.values_list('animal_id', flat=True))
    }
    
    return render(request, 'core/compras/form.html', context)

@login_required
def detalhe_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk, usuario=request.user)
    animais_compra = CompraAnimal.objects.filter(compra=compra)
    
    valor_total = sum(animal_compra.valor_total for animal_compra in animais_compra)
    
    context = {
        'compra': compra,
        'animais_compra': animais_compra,
        'valor_total': valor_total
    }
    
    return render(request, 'core/compras/detalhe.html', context)

@login_required
def excluir_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        # Limpa o valor de compra dos animais
        for animal_compra in compra.animais.all():
            animal = animal_compra.animal
            animal.valor_compra = None
            animal.save()
        
        compra.delete()
        messages.success(request, 'Compra excluída com sucesso!')
        return redirect('compras_list')
    
    context = {
        'compra': compra
    }
    
    return render(request, 'core/compras/excluir.html', context)

@login_required
def get_peso_entrada(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    return JsonResponse({
        'peso_entrada': float(animal.peso_entrada) if animal.peso_entrada else None
    })
