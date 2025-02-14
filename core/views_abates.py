from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from .models import Animal, Fazenda, Lote, Pesagem
from .models_abates import Abate, AbateAnimal, ParcelaAbate, PagamentoParcelaAbate
from .forms import AbateForm

def get_peso_atual(animal):
    """Retorna o peso atual do animal"""
    ultimo_peso = Pesagem.objects.filter(animal=animal).order_by('-data').values('peso').first()
    if ultimo_peso:
        return ultimo_peso['peso']
    return animal.primeiro_peso or 0

@login_required
def lista_abates(request):
    # Filtros
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    # Query base
    abates = Abate.objects.filter(usuario=request.user)
    
    # Aplicar filtros
    if search_query:
        abates = abates.filter(
            Q(comprador__nome__icontains=search_query) |
            Q(animais__animal__brinco_visual__icontains=search_query)
        ).distinct()
    
    if status:
        abates = abates.filter(status=status)
    
    if data_inicio:
        abates = abates.filter(data__gte=data_inicio)
    
    if data_fim:
        abates = abates.filter(data__lte=data_fim)
    
    # Ordenação
    abates = abates.order_by('-data', '-id')
    
    # Calcula os totais por status
    totais_status = abates.annotate(
        total_valor=Sum('animais__valor_total')
    ).aggregate(
        total_pago=Sum(Case(
            When(status='PAGO', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_pendente=Sum(Case(
            When(status='PENDENTE', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_vencido=Sum(Case(
            When(status='VENCIDO', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_geral=Sum('total_valor'),
        count_pago=Count(Case(When(status='PAGO', then=1))),
        count_pendente=Count(Case(When(status='PENDENTE', then=1))),
        count_vencido=Count(Case(When(status='VENCIDO', then=1))),
    )
    
    context = {
        'abates': abates,
        'total_abates': abates.count(),
        'abates_pagos': totais_status['count_pago'],
        'abates_pendentes': totais_status['count_pendente'],
        'abates_vencidos': totais_status['count_vencido'],
        'valor_total_pago': totais_status['total_pago'] or 0,
        'valor_total_pendente': totais_status['total_pendente'] or 0,
        'valor_total_vencido': totais_status['total_vencido'] or 0,
        'valor_total_geral': totais_status['total_geral'] or 0,
        'search_query': search_query,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'core/abates/lista.html', context)

def criar_parcelas_abate(abate, valor_total):
    """Cria as parcelas para um abate"""
    valor_parcela = valor_total / abate.numero_parcelas
    data_vencimento = abate.data_vencimento
    
    parcelas = []
    for i in range(abate.numero_parcelas):
        parcela = ParcelaAbate(
            abate=abate,
            numero=i + 1,
            data_vencimento=data_vencimento,
            valor=valor_parcela,
            status='PENDENTE'
        )
        parcelas.append(parcela)
        data_vencimento += timedelta(days=abate.intervalo_parcelas)
    
    ParcelaAbate.objects.bulk_create(parcelas)

@login_required
def criar_abate(request):
    if request.method == 'POST':
        form = AbateForm(request.POST, usuario=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():  # Inicia uma transação
                    abate = form.save(commit=False)
                    abate.usuario = request.user
                    abate.save()  # Salva o abate primeiro

                    # Processa os animais selecionados
                    animais_ids = request.POST.getlist('animal')
                    if not animais_ids:
                        messages.error(request, 'Selecione pelo menos um animal.')
                        raise ValueError('Nenhum animal selecionado')

                    valor_total = Decimal('0')
                    animais_abate = []
                    for animal_id in animais_ids:
                        animal = Animal.objects.get(id=animal_id, usuario=request.user)
                        peso_atual = get_peso_atual(animal)
                        
                        # Cria o objeto AbateAnimal mas não salva ainda
                        abate_animal = AbateAnimal(
                            abate=abate,
                            animal=animal,
                            peso_vivo=peso_atual,
                            rendimento=abate.rendimento_padrao,
                            valor_arroba=abate.valor_arroba
                        )
                        # Calcula o valor total baseado no peso em @ e valor por @
                        valor = abate_animal.peso_arroba() * abate.valor_arroba
                        abate_animal.valor_total = valor
                        
                        animais_abate.append(abate_animal)
                        valor_total += valor
                        
                        # Atualiza o status do animal para abatido
                        animal.situacao = 'ABATIDO'
                        animal.save()
                    
                    # Salva todos os animais do abate de uma vez
                    AbateAnimal.objects.bulk_create(animais_abate)
                    
                    # Cria as parcelas
                    criar_parcelas_abate(abate, valor_total)

                messages.success(request, 'Abate registrado com sucesso!')
                return redirect('abates_list')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Erro ao salvar abate: {str(e)}')
    else:
        form = AbateForm(usuario=request.user)
    
    context = {
        'form': form,
        'animais_disponiveis': Animal.objects.filter(
            usuario=request.user, 
            situacao='ATIVO'
        ).select_related('fazenda_atual', 'lote').order_by('brinco_visual'),
        'animais_selecionados': [],  # Lista vazia para novo abate
        'fazendas': Fazenda.objects.filter(usuario=request.user),
        'lotes': Lote.objects.filter(usuario=request.user)
    }
    return render(request, 'core/abates/form.html', context)

@login_required
def editar_abate(request, pk):
    abate = get_object_or_404(Abate, pk=pk, usuario=request.user)
    if request.method == 'POST':
        form = AbateForm(request.POST, instance=abate, usuario=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():  # Inicia uma transação
                    # Salva o abate primeiro
                    abate = form.save()

                    # Processa os animais selecionados
                    animais_ids = request.POST.getlist('animal')
                    if not animais_ids:
                        messages.error(request, 'Selecione pelo menos um animal.')
                        raise ValueError('Nenhum animal selecionado')

                    # Reativa animais que foram removidos do abate
                    animais_removidos = AbateAnimal.objects.filter(abate=abate).exclude(
                        animal_id__in=animais_ids
                    ).values_list('animal_id', flat=True)
                    
                    # Atualiza o status dos animais removidos para ATIVO
                    Animal.objects.filter(id__in=animais_removidos).update(situacao='ATIVO')

                    # Remove animais não selecionados
                    AbateAnimal.objects.filter(abate=abate).exclude(animal_id__in=animais_ids).delete()

                    # Remove as parcelas existentes
                    ParcelaAbate.objects.filter(abate=abate).delete()

                    # Atualiza ou cria novos animais
                    valor_total = Decimal('0')
                    for animal_id in animais_ids:
                        animal = Animal.objects.get(id=animal_id, usuario=request.user)
                        peso_atual = get_peso_atual(animal)
                        
                        # Atualiza ou cria o AbateAnimal
                        abate_animal, created = AbateAnimal.objects.update_or_create(
                            abate=abate,
                            animal=animal,
                            defaults={
                                'peso_vivo': peso_atual,
                                'rendimento': abate.rendimento_padrao,
                                'valor_arroba': abate.valor_arroba
                            }
                        )
                        
                        # Recalcula o valor total
                        valor = abate_animal.peso_arroba() * abate.valor_arroba
                        abate_animal.valor_total = valor
                        abate_animal.save()
                        
                        valor_total += valor
                        
                        # Atualiza o status do animal para abatido
                        animal.situacao = 'ABATIDO'
                        animal.save()
                    
                    # Cria novas parcelas
                    criar_parcelas_abate(abate, valor_total)

                messages.success(request, 'Abate atualizado com sucesso!')
                return redirect('abates_list')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = AbateForm(instance=abate, usuario=request.user)
    
    context = {
        'form': form,
        'abate': abate,
        'animais_disponiveis': Animal.objects.filter(
            usuario=request.user, 
            situacao__in=['ATIVO', 'ABATIDO']
        ).order_by('brinco_visual'),
        'animais_selecionados': [aa.animal_id for aa in abate.animais.all()],
        'fazendas': Fazenda.objects.filter(usuario=request.user),
        'lotes': Lote.objects.filter(usuario=request.user)
    }
    return render(request, 'core/abates/form.html', context)

@login_required
def detalhe_abate(request, pk):
    abate = get_object_or_404(Abate, pk=pk, usuario=request.user)
    # Força a atualização do status antes de mostrar os detalhes
    abate.atualizar_status()
    
    parcelas = ParcelaAbate.objects.filter(abate=abate).order_by('numero')
    animais = AbateAnimal.objects.filter(abate=abate)
    
    context = {
        'abate': abate,
        'parcelas': parcelas,
        'animais': animais,
    }
    return render(request, 'core/abates/detalhe.html', context)

@login_required
def excluir_abate(request, pk):
    abate = get_object_or_404(Abate, pk=pk, usuario=request.user)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # O método delete do AbateAnimal já cuida de restaurar o status dos animais
                abate.delete()
                messages.success(request, 'Abate excluído com sucesso!')
                return redirect('abates_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir abate: {str(e)}')
            return redirect('abates_list')
    return render(request, 'core/abates/excluir.html', {'abate': abate})

@login_required
def registrar_pagamento_abate(request, parcela_id):
    parcela = get_object_or_404(ParcelaAbate, id=parcela_id, abate__usuario=request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                valor = Decimal(request.POST.get('valor', '0'))
                data_pagamento = request.POST.get('data_pagamento')
                
                if valor <= 0:
                    raise ValueError('O valor do pagamento deve ser maior que zero.')
                
                if valor > parcela.valor_restante:
                    raise ValueError('O valor do pagamento não pode ser maior que o valor restante da parcela.')
                
                # Registra o pagamento
                pagamento = PagamentoParcelaAbate.objects.create(
                    parcela=parcela,
                    valor=valor,
                    data_pagamento=data_pagamento
                )
                
                # Atualiza o valor pago da parcela
                parcela.valor_pago += valor
                if parcela.valor_pago >= parcela.valor:
                    parcela.status = 'PAGO'
                    parcela.data_pagamento = data_pagamento
                parcela.save()
                
                print(f"Parcela {parcela.id} atualizada para status {parcela.status}")
                # Força a atualização do status do abate
                parcela.abate.refresh_from_db()
                parcela.abate.atualizar_status()
            
            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('abates_detalhe', pk=parcela.abate.id)
            
        except ValueError as e:
            messages.error(request, str(e))
    
    context = {
        'parcela': parcela,
    }
    return render(request, 'core/abates/registrar_pagamento.html', context)

@login_required
def historico_pagamentos_abate(request, parcela_id):
    parcela = get_object_or_404(ParcelaAbate, id=parcela_id, abate__usuario=request.user)
    pagamentos = PagamentoParcelaAbate.objects.filter(parcela=parcela).order_by('-data_pagamento')
    
    context = {
        'parcela': parcela,
        'pagamentos': pagamentos,
    }
    return render(request, 'core/abates/historico_pagamentos.html', context)

@login_required
def imprimir_abates(request):
    # Filtros
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    # Query base
    abates = Abate.objects.filter(usuario=request.user)
    
    # Aplicar filtros
    if search_query:
        abates = abates.filter(
            Q(comprador__nome__icontains=search_query) |
            Q(animais__animal__brinco_visual__icontains=search_query)
        ).distinct()
    
    if status:
        abates = abates.filter(status=status)
    
    if data_inicio:
        abates = abates.filter(data__gte=data_inicio)
    
    if data_fim:
        abates = abates.filter(data__lte=data_fim)
    
    # Ordenação
    abates = abates.order_by('-data', '-id')
    
    # Calcula os totais por status
    totais_status = abates.annotate(
        total_valor=Sum('animais__valor_total')
    ).aggregate(
        total_pago=Sum(Case(
            When(status='PAGO', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_pendente=Sum(Case(
            When(status='PENDENTE', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_vencido=Sum(Case(
            When(status='VENCIDO', then=F('total_valor')),
            default=0,
            output_field=DecimalField()
        )),
        total_geral=Sum('total_valor'),
        count_pago=Count(Case(When(status='PAGO', then=1))),
        count_pendente=Count(Case(When(status='PENDENTE', then=1))),
        count_vencido=Count(Case(When(status='VENCIDO', then=1))),
    )
    
    context = {
        'abates': abates,
        'total_abates': abates.count(),
        'abates_pagos': totais_status['count_pago'],
        'abates_pendentes': totais_status['count_pendente'],
        'abates_vencidos': totais_status['count_vencido'],
        'valor_total_pago': totais_status['total_pago'] or 0,
        'valor_total_pendente': totais_status['total_pendente'] or 0,
        'valor_total_vencido': totais_status['total_vencido'] or 0,
        'valor_total_geral': totais_status['total_geral'] or 0,
        'search_query': search_query,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'core/abates/imprimir.html', context)

@login_required
def get_peso_atual_json(request):
    """Retorna o peso atual do animal em formato JSON"""
    try:
        animal_id = request.GET.get('animal_id')
        if not animal_id:
            return JsonResponse({'error': 'ID do animal não fornecido'}, status=400)
            
        animal = get_object_or_404(Animal, pk=animal_id, usuario=request.user)
        peso = get_peso_atual(animal)
        return JsonResponse({'peso': float(peso)})
    except Animal.DoesNotExist:
        return JsonResponse({'error': 'Animal não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
