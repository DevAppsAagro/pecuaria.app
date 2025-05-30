from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import F, Sum, Subquery, OuterRef, DecimalField, Q, Max, Value
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils import timezone
from .models import Animal, Fazenda, Lote, Pesagem, Contato, ContaBancaria
from .models_vendas import Venda, VendaAnimal
from .models_parcelas_venda import ParcelaVenda
from .models_pagamentos_venda import PagamentoVenda
from .forms_vendas import VendaForm
import logging
from django.db.models import Sum

@login_required
def lista_vendas(request):
    search_query = request.GET.get('search', '')
    vendas = Venda.objects.filter(usuario=request.user)

    if search_query:
        vendas = vendas.filter(
            Q(comprador__nome__icontains=search_query) |
            Q(animais__animal__brinco_visual__icontains=search_query)
        ).distinct()

    # Filtros
    status = request.GET.get('status')
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    if status:
        vendas = vendas.filter(status=status)
    if data_inicial:
        vendas = vendas.filter(data__gte=data_inicial)
    if data_final:
        vendas = vendas.filter(data__lte=data_final)

    # Totais por status
    totais_status = {
        'PAGO': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'PENDENTE': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'VENCE_HOJE': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'},
        'VENCIDO': {'valor': Decimal('0.00'), 'valor_formatado': 'R$ 0,00'}
    }

    hoje = timezone.now().date()

    for venda in vendas:
        # Calcula o valor total da venda somando o valor_total de cada animal
        valor_total = sum(Decimal(str(animal.valor_total)) for animal in venda.animais.all())
        
        if venda.status == 'PAGO':
            totais_status['PAGO']['valor'] += valor_total
        elif venda.data_vencimento == hoje:
            totais_status['VENCE_HOJE']['valor'] += valor_total
        elif venda.data_vencimento < hoje:
            totais_status['VENCIDO']['valor'] += valor_total
        else:
            totais_status['PENDENTE']['valor'] += valor_total

    # Formata os valores
    for status in totais_status:
        totais_status[status]['valor_formatado'] = f"R$ {totais_status[status]['valor']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

    context = {
        'vendas': vendas,
        'search_query': search_query,
        'totais_status': totais_status,
        'status_filter': status,
        'data_inicial': data_inicial,
        'data_final': data_final
    }

    return render(request, 'core/vendas/lista.html', context)

def criar_parcelas_venda(venda, valor_total):
    """Cria as parcelas para uma venda"""
    # Garante que o valor_total seja um Decimal
    valor_total = Decimal(str(valor_total))
    
    # Calcula o valor de cada parcela
    valor_parcela = valor_total / Decimal(str(venda.numero_parcelas))
    valor_parcela = valor_parcela.quantize(Decimal('.01'))  # Arredonda para 2 casas decimais
    
    # Ajusta o valor da última parcela para compensar arredondamentos
    valor_ultima = valor_total - (valor_parcela * (venda.numero_parcelas - 1))
    valor_ultima = valor_ultima.quantize(Decimal('.01'))  # Arredonda para 2 casas decimais
    
    # Cria as parcelas
    parcelas = []
    for i in range(venda.numero_parcelas):
        data_vencimento = venda.data_vencimento + timedelta(days=i * venda.intervalo_parcelas)
        valor = valor_ultima if i == venda.numero_parcelas - 1 else valor_parcela
        
        parcelas.append(ParcelaVenda(
            venda=venda,
            numero=i + 1,
            valor=valor,
            data_vencimento=data_vencimento
        ))
    
    # Salva todas as parcelas de uma vez
    ParcelaVenda.objects.bulk_create(parcelas)

@login_required
def criar_venda(request):
    logger = logging.getLogger(__name__)
    logger.info('Iniciando criação de venda')
    
    # Obtém os parâmetros de filtro
    fazenda_id = request.GET.get('fazenda')
    lote_id = request.GET.get('lote')
    
    logger.debug(f'Parâmetros de filtro: fazenda_id={fazenda_id}, lote_id={lote_id}')
    
    # Filtra apenas animais ativos
    animais_disponiveis = Animal.objects.filter(
        usuario=request.user,
        situacao='ATIVO'
    ).select_related(
        'fazenda_atual',
        'lote'
    )
    
    # Aplica os filtros se fornecidos
    if fazenda_id:
        animais_disponiveis = animais_disponiveis.filter(fazenda_atual_id=fazenda_id)
    if lote_id:
        animais_disponiveis = animais_disponiveis.filter(lote_id=lote_id)
    
    logger.debug(f'Query SQL animais_disponiveis: {animais_disponiveis.query}')
    logger.info(f'Total de animais disponíveis: {animais_disponiveis.count()}')
    
    # Obtém as fazendas do usuário
    fazendas = Fazenda.objects.filter(usuario=request.user)
    logger.debug(f'Total de fazendas: {fazendas.count()}')
    
    # Obtém os lotes do usuário, filtrados por fazenda se uma fazenda foi selecionada
    lotes = Lote.objects.filter(usuario=request.user)
    if fazenda_id:
        lotes = lotes.filter(fazenda_id=fazenda_id)
    logger.debug(f'Total de lotes: {lotes.count()}')
    
    # Filtra apenas contatos do tipo comprador
    compradores = Contato.objects.filter(
        usuario=request.user,
        tipo='CO'
    )
    logger.debug(f'Total de compradores: {compradores.count()}')
    
    # Filtra contas bancárias ativas
    contas = ContaBancaria.objects.filter(
        usuario=request.user,
        ativa=True
    )
    logger.debug(f'Total de contas bancárias: {contas.count()}')
    
    if request.method == 'POST':
        logger.info('Recebido POST para criar venda')
        logger.debug(f'POST data: {request.POST}')
        
        form = VendaForm(request.POST, usuario=request.user)
        if form.is_valid():
            logger.info('Formulário é válido')
            try:
                # Obtém os IDs dos animais
                animais_ids = request.POST.getlist('animal')
                logger.debug(f'IDs dos animais selecionados: {animais_ids}')
                
                if not animais_ids:
                    logger.error('Nenhum animal selecionado')
                    messages.error(request, 'Selecione pelo menos um animal.')
                    raise ValueError('Nenhum animal selecionado')

                # Verifica se algum animal já está vendido
                animais_vendidos = Animal.objects.filter(
                    id__in=animais_ids,
                    situacao='VENDIDO'
                ).values_list('brinco_visual', flat=True)
                
                if animais_vendidos:
                    mensagem = f'Os seguintes animais já estão vendidos: {", ".join(animais_vendidos)}'
                    logger.error(mensagem)
                    messages.error(request, mensagem)
                    raise ValueError(mensagem)

                # Inicia uma transação para verificar e atualizar os animais
                with transaction.atomic():
                    # Verifica se todos os animais estão disponíveis antes de processar
                    animais_disponiveis = Animal.objects.select_for_update().filter(
                        id__in=animais_ids,
                        usuario=request.user,
                        situacao='ATIVO'
                    )
                    
                    # Obtém os IDs dos animais que estão realmente disponíveis
                    ids_disponiveis = set(animais_disponiveis.values_list('id', flat=True))
                ids_solicitados = set(map(int, animais_ids))
                
                # Verifica se há animais não disponíveis
                animais_nao_disponiveis = ids_solicitados - ids_disponiveis
                
                if animais_nao_disponiveis:
                    # Obtém os brincos dos animais não disponíveis para mensagem mais detalhada
                    brincos_nao_disponiveis = Animal.objects.filter(
                        id__in=animais_nao_disponiveis
                    ).values_list('brinco_visual', flat=True)
                    
                    mensagem = f'Os seguintes animais não estão disponíveis: {", ".join(brincos_nao_disponiveis)}'
                    logger.error(mensagem)
                    messages.error(request, mensagem)
                    return render(request, 'core/vendas/form.html', {
                        'form': form,
                        'animais_disponiveis': animais_disponiveis,
                        'fazendas': fazendas,
                        'lotes': lotes,
                        'fazenda_selecionada': fazenda_id,
                        'lote_selecionado': lote_id,
                        'compradores': compradores,
                        'contas': contas
                    })

                with transaction.atomic():
                    # Primeiro, salva a venda
                    venda = form.save(commit=False)
                    venda.usuario = request.user
                    venda.save()
                    logger.info(f'Venda {venda.id} criada com sucesso')

                    # Verifica se a venda foi realmente criada
                    if not venda.id:
                        logger.error('Venda não foi criada corretamente')
                        messages.error(request, 'Erro ao criar venda. Por favor, tente novamente.')
                        raise ValueError('Venda não foi criada corretamente')

                    # Processa os animais já validados
                    valor_total = Decimal('0')
                    
                    for animal in animais_disponiveis:
                        try:
                            peso_atual = Decimal(str(get_peso_atual(animal)))
                            logger.debug(f'Peso atual do animal {animal.brinco_visual}: {peso_atual}')
                            
                            # Calcula o valor do animal
                            if form.cleaned_data['tipo_venda'] == 'KG':
                                valor = peso_atual * Decimal(str(form.cleaned_data['valor_unitario']))
                            else:
                                valor = Decimal(str(form.cleaned_data['valor_unitario']))
                            
                            # Arredonda o valor para 2 casas decimais
                            valor = valor.quantize(Decimal('.01'))
                            logger.debug(f'Valor calculado para o animal {animal.brinco_visual}: {valor}')
                            
                            # Cria e salva o objeto VendaAnimal
                            venda_animal = VendaAnimal(
                                venda=venda,
                                animal=animal,
                                peso_venda=peso_atual,
                                valor_kg=form.cleaned_data['valor_unitario'] if form.cleaned_data['tipo_venda'] == 'KG' else None,
                                valor_total=valor
                            )
                            venda_animal.save()
                            
                            # Atualiza o status do animal para VENDIDO
                            animal.situacao = 'VENDIDO'
                            animal.save()
                            
                            valor_total += valor
                            logger.debug(f'Animal {animal.brinco_visual} processado com sucesso')
                        except Exception as e:
                            logger.error(f'Erro ao processar animal {animal.brinco_visual}: {str(e)}')
                            raise
                    
                    logger.info(f'Todos os animais processados com sucesso')

                    # Atualiza o valor total da venda
                    venda.save()
                    logger.info(f'Valor total da venda: {venda.valor_total}')

                    # Se tiver data de pagamento, cria uma única parcela já paga
                    if venda.data_pagamento:
                        logger.info('Criando parcela única para venda paga')
                        parcela = ParcelaVenda.objects.create(
                            venda=venda,
                            numero=1,
                            valor=valor_total,
                            data_vencimento=venda.data_pagamento,
                            status='PAGO'
                        )
                        
                        # Cria o pagamento
                        PagamentoVenda.objects.create(
                            parcela=parcela,
                            valor=valor_total,
                            data_pagamento=venda.data_pagamento
                        )
                        logger.info('Parcela e pagamento criados com sucesso')
                    # Se não tiver data de pagamento, cria as parcelas normalmente
                    else:
                        logger.info('Criando parcelas para venda')
                        criar_parcelas_venda(venda, valor_total)

                messages.success(request, 'Venda criada com sucesso!')
                logger.info('Venda criada com sucesso, redirecionando')
                return redirect('lista_vendas')
                
            except Animal.DoesNotExist:
                logger.error('Animal não encontrado ou não está mais disponível')
                messages.error(request, 'Um ou mais animais não estão mais disponíveis. Por favor, atualize a página e tente novamente.')
            except ValueError as e:
                logger.error(f'Erro de validação: {str(e)}')
                messages.error(request, str(e))
            except Exception as e:
                logger.exception('Erro ao criar venda:')
                messages.error(request, f'Erro ao criar venda: {str(e)}')
        else:
            logger.error(f'Formulário inválido. Erros: {form.errors}')
    else:
        form = VendaForm(usuario=request.user)
    
    return render(request, 'core/vendas/form.html', {
        'form': form,
        'animais_disponiveis': animais_disponiveis,
        'fazendas': fazendas,
        'lotes': lotes,
        'fazenda_selecionada': fazenda_id,
        'lote_selecionado': lote_id,
        'compradores': compradores,
        'contas': contas
    })

@login_required
def editar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk, usuario=request.user)
    if request.method == 'POST':
        form = VendaForm(request.POST, instance=venda, usuario=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():  # Inicia uma transação
                    # Salva a venda primeiro
                    venda = form.save()

                    # Processa os animais selecionados
                    animais_ids = request.POST.getlist('animal')
                    if not animais_ids:
                        messages.error(request, 'Selecione pelo menos um animal.')
                        raise ValueError('Nenhum animal selecionado')

                    # Reativa animais que foram removidos da venda
                    VendaAnimal.objects.filter(venda=venda).exclude(
                        animal_id__in=animais_ids
                    ).update(animal__situacao='ATIVO')

                    # Remove animais não selecionados
                    VendaAnimal.objects.filter(venda=venda).exclude(animal_id__in=animais_ids).delete()

                    # Remove as parcelas existentes
                    ParcelaVenda.objects.filter(venda=venda).delete()

                    # Atualiza ou cria novos animais
                    valor_total = Decimal('0')
                    for animal_id in animais_ids:
                        animal = Animal.objects.get(id=animal_id, usuario=request.user)
                        peso_atual = get_peso_atual(animal)
                        valor = (Decimal(str(peso_atual)) * venda.valor_unitario 
                                if venda.tipo_venda == 'KG' 
                                else venda.valor_unitario)
                        
                        VendaAnimal.objects.update_or_create(
                            venda=venda,
                            animal=animal,
                            defaults={
                                'valor_total': valor,
                                'peso_venda': peso_atual,
                                'valor_kg': venda.valor_unitario  # Sempre salvar o valor unitário como valor_kg
                            }
                        )
                        valor_total += valor
                    
                    # Cria as parcelas
                    criar_parcelas_venda(venda, valor_total)

                messages.success(request, 'Venda atualizada com sucesso!')
                return redirect('lista_vendas')
            except ValueError as e:
                # Erro de validação (ex: nenhum animal selecionado)
                messages.error(request, str(e))
                return render(request, 'core/vendas/form.html', {'form': form})
            except Exception as e:
                # Outros erros
                messages.error(request, f'Erro ao atualizar a venda: {str(e)}')
                return render(request, 'core/vendas/form.html', {'form': form})
    else:
        form = VendaForm(instance=venda, usuario=request.user)
    
    # Pega o último peso de cada animal
    animais = Animal.objects.filter(
        Q(situacao='ATIVO') | Q(vendaanimal__venda=venda),
        usuario=request.user
    ).annotate(
        ultimo_peso=Coalesce(
            Subquery(
                Pesagem.objects.filter(
                    animal=OuterRef('pk')
                ).order_by('-data').values('peso')[:1]
            ),
            F('primeiro_peso'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
        peso_atual=F('ultimo_peso')
    ).distinct()
    
    context = {
        'form': form,
        'venda': venda,
        'animais_disponiveis': animais,
        'fazendas': Fazenda.objects.filter(usuario=request.user),
        'lotes': Lote.objects.filter(usuario=request.user),
        'animais_selecionados': [
            animal.id for animal in Animal.objects.filter(vendaanimal__venda=venda)
        ]
    }
    return render(request, 'core/vendas/form.html', context)

@login_required
def detalhe_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk, usuario=request.user)
    
    # Carrega as parcelas com seus pagamentos
    parcelas = ParcelaVenda.objects.filter(venda=venda).order_by('numero').annotate(
        valor_pago_calc=Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField()),
        valor_restante_calc=F('valor') - Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField())
    )
    
    # Se a venda tem data de pagamento, todas as parcelas devem estar pagas
    if venda.data_pagamento:
        parcelas.update(status='PAGO')
    else:
        # Atualiza o status de cada parcela baseado no valor pago
        for parcela in parcelas:
            if parcela.valor_pago_calc >= parcela.valor:
                parcela.status = 'PAGO'
            elif parcela.valor_pago_calc > 0:
                parcela.status = 'PARCIAL'
            elif parcela.data_vencimento < timezone.now().date():
                parcela.status = 'VENCIDO'
            else:
                parcela.status = 'PENDENTE'
            parcela.save()
    
    animais = VendaAnimal.objects.filter(venda=venda)
    
    context = {
        'venda': venda,
        'parcelas': parcelas,
        'animais': animais,
    }
    return render(request, 'core/vendas/detalhe.html', context)

@login_required
def excluir_venda(request, pk):
    try:
        venda = get_object_or_404(Venda, pk=pk, usuario=request.user)
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Reativa todos os animais da venda
                    Animal.objects.filter(vendaanimal__venda=venda).update(situacao='ATIVO')
                    
                    # Exclui a venda (isso vai excluir automaticamente as parcelas e vendaanimal por causa do on_delete=CASCADE)
                    venda.delete()
                    
                messages.success(request, 'Venda excluída com sucesso!')
                return redirect('lista_vendas')
            except Exception as e:
                messages.error(request, f'Erro ao excluir venda: {str(e)}')
                return redirect('detalhe_venda', pk=pk)
        
        # Se for GET, mostra a página de confirmação
        animais = VendaAnimal.objects.filter(venda=venda)
        return render(request, 'core/vendas/confirmar_exclusao.html', {
            'venda': venda,
            'animais': animais
        })
        
    except Venda.DoesNotExist:
        messages.error(request, 'Venda não encontrada.')
        return redirect('lista_vendas')

@login_required
def get_peso_atual_json(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    peso_atual = get_peso_atual(animal)
    return JsonResponse({'peso': peso_atual})

@login_required
def registrar_pagamento_venda(request, parcela_id):
    # Carrega a parcela com seus pagamentos e valores calculados
    parcela = get_object_or_404(
        ParcelaVenda.objects.annotate(
            valor_pago_calc=Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField()),
            valor_restante_calc=F('valor') - Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField())
        ),
        pk=parcela_id,
        venda__usuario=request.user
    )
    
    if request.method == 'POST':
        try:
            valor_pago = Decimal(request.POST.get('valor_pago', '0'))
            data_pagamento = request.POST.get('data_pagamento')
            
            if not valor_pago or valor_pago <= 0:
                raise ValueError('O valor do pagamento deve ser maior que zero')
            
            valor_restante = parcela.valor_restante_calc or parcela.valor
            if valor_pago > valor_restante:
                raise ValueError('O valor do pagamento não pode ser maior que o valor restante da parcela')
            
            with transaction.atomic():
                # Cria o pagamento
                PagamentoVenda.objects.create(
                    parcela=parcela,
                    valor=valor_pago,
                    data_pagamento=data_pagamento
                )
                
                # Atualiza o status da parcela
                parcela.atualizar_status()
                parcela.save()
                
                # Verifica se todas as parcelas estão pagas
                venda = parcela.venda
                parcelas_pendentes = ParcelaVenda.objects.filter(
                    venda=venda
                ).annotate(
                    valor_pago=Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField())
                ).filter(valor_pago__lt=F('valor')).count()
                
                # Se não há parcelas pendentes, atualiza o status da venda para PAGO
                if parcelas_pendentes == 0:
                    venda.data_pagamento = timezone.now().date()
                    venda.status = 'PAGO'
                    venda.save()
            
            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('detalhe_venda', pk=parcela.venda.id)
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erro ao registrar pagamento: {str(e)}')
    
    return render(request, 'core/vendas/registrar_pagamento.html', {'parcela': parcela})

@login_required
def historico_pagamentos_venda(request, parcela_id):
    # Carrega a parcela com seus pagamentos e valores calculados
    parcela = get_object_or_404(
        ParcelaVenda.objects.annotate(
            valor_pago_calc=Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField()),
            valor_restante_calc=F('valor') - Coalesce(Sum('pagamentos_venda__valor'), 0, output_field=DecimalField())
        ),
        pk=parcela_id,
        venda__usuario=request.user
    )
    
    # Busca os pagamentos ordenados por data
    pagamentos = PagamentoVenda.objects.filter(parcela=parcela).order_by('-data_pagamento')
    
    context = {
        'parcela': parcela,
        'pagamentos': pagamentos,
        'valor_pago': parcela.valor_pago_calc,
        'valor_restante': parcela.valor_restante_calc
    }
    return render(request, 'core/vendas/historico_pagamentos.html', context)

def get_peso_atual(animal):
    """Retorna o peso atual do animal"""
    ultimo_peso = Pesagem.objects.filter(animal=animal).order_by('-data').values('peso').first()
    if ultimo_peso:
        return ultimo_peso['peso']
    return animal.primeiro_peso or 0

def get_animais_por_lote(request):
    """Retorna lista de animais filtrados por fazenda e lote em formato JSON"""
    logger = logging.getLogger(__name__)
    logger.info('Iniciando get_animais_por_lote')
    
    fazenda_id = request.GET.get('fazenda_id')
    lote_id = request.GET.get('lote_id')
    
    logger.debug(f'Parâmetros recebidos: fazenda_id={fazenda_id}, lote_id={lote_id}')
    
    if not (fazenda_id and lote_id):
        logger.error('Fazenda e lote são obrigatórios')
        return JsonResponse({'error': 'Fazenda e lote são obrigatórios'}, status=400)
    
    try:
        # Filtra apenas animais ativos no lote/fazenda selecionados
        query = Animal.objects.filter(
            usuario=request.user,
            situacao='ATIVO',
            fazenda_atual_id=fazenda_id,
            lote_id=lote_id
        ).exclude(
            # Exclui animais que já estão em uma venda
            vendaanimal__isnull=False
        ).select_related('lote')
        
        logger.debug(f'Query SQL: {query.query}')
        
        animais = query.order_by('brinco_visual')
        logger.info(f'Total de animais encontrados: {animais.count()}')
        
        data = []
        for animal in animais:
            peso_atual = get_peso_atual(animal)
            data.append({
                'id': animal.id,
                'brinco_visual': animal.brinco_visual,
                'lote': animal.lote.id_lote if animal.lote else '-',
                'peso_atual': peso_atual
            })
        
        logger.info('Dados dos animais preparados com sucesso')
        return JsonResponse({'animais': data})
        
    except Exception as e:
        logger.exception('Erro ao buscar animais:')
        return JsonResponse({'error': str(e)}, status=500)
