from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, F, OuterRef, Subquery, Max, Q, Avg
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from .models_estoque import Insumo, MovimentacaoEstoque, RateioMovimentacao
from .models import (
    Lote, Animal, Fazenda, CategoriaCusto, SubcategoriaCusto, 
    Pesagem, UnidadeMedida, Pasto
)

@login_required
def estoque_list(request):
    mostrar_inativos = request.GET.get('mostrar_inativos', 'false') == 'true'
    
    # Filtra os insumos do usuário
    insumos = Insumo.objects.filter(usuario=request.user)
    
    # Se não estiver mostrando inativos, filtra apenas os ativos
    if not mostrar_inativos:
        insumos = insumos.filter(ativo=True)
    
    # Calcula o valor total em estoque
    total_valor_estoque = sum(insumo.valor_total for insumo in insumos)
    
    # Conta o número de categorias distintas
    categorias_ids = set()
    for insumo in insumos:
        if insumo.categoria_id:
            categorias_ids.add(insumo.categoria_id)
    total_categorias = len(categorias_ids)
    
    # Conta insumos com estoque baixo (menos de 5 unidades)
    insumos_estoque_baixo = 0
    for insumo in insumos:
        if insumo.saldo_estoque < 5:  # Consideramos estoque baixo se tiver menos de 5 unidades
            insumos_estoque_baixo += 1
    
    return render(request, 'estoque/estoque_list.html', {
        'insumos': insumos,
        'mostrar_inativos': mostrar_inativos,
        'total_valor_estoque': total_valor_estoque,
        'total_categorias': total_categorias,
        'insumos_estoque_baixo': insumos_estoque_baixo
    })

@login_required
def insumo_create(request):
    if request.method == 'POST':
        try:
            insumo = Insumo(
                nome=request.POST['nome'],
                categoria_id=request.POST['categoria'],
                subcategoria_id=request.POST['subcategoria'],
                unidade_medida_id=request.POST['unidade_medida'],
                usuario=request.user
            )
            insumo.save()
            messages.success(request, 'Insumo criado com sucesso!')
            return redirect('estoque_list')
        except Exception as e:
            messages.error(request, f'Erro ao criar insumo: {str(e)}')
    
    # Busca categorias do usuário com alocação 'estoque'
    categorias_usuario = CategoriaCusto.objects.filter(usuario=request.user, alocacao='estoque')
    
    # Busca categorias globais relacionadas a estoque
    categorias_globais = CategoriaCusto.objects.filter(
        usuario__isnull=True
    ).filter(
        Q(nome__icontains='Estoque') | 
        Q(nome__icontains='Insumo') | 
        Q(nome__icontains='Ração') | 
        Q(nome__icontains='Medicamento') | 
        Q(nome__icontains='Vacina') | 
        Q(nome__icontains='Suplemento')
    )
    
    # Combina as duas queryset
    categorias = categorias_usuario.union(categorias_globais)
    
    unidades = UnidadeMedida.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'estoque/insumo_form.html', {
        'categorias': categorias,
        'unidades': unidades
    })

@login_required
def insumo_edit(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk, usuario=request.user)
    if request.method == 'POST':
        try:
            insumo.nome = request.POST['nome']
            insumo.categoria_id = request.POST['categoria']
            insumo.subcategoria_id = request.POST['subcategoria']
            insumo.unidade_medida_id = request.POST['unidade_medida']
            insumo.save()
            messages.success(request, 'Insumo atualizado com sucesso!')
            return redirect('estoque_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar insumo: {str(e)}')
    
    # Busca categorias do usuário com alocação 'estoque'
    categorias_usuario = CategoriaCusto.objects.filter(usuario=request.user, alocacao='estoque')
    
    # Busca categorias globais relacionadas a estoque
    categorias_globais = CategoriaCusto.objects.filter(
        usuario__isnull=True
    ).filter(
        Q(nome__icontains='Estoque') | 
        Q(nome__icontains='Insumo') | 
        Q(nome__icontains='Ração') | 
        Q(nome__icontains='Medicamento') | 
        Q(nome__icontains='Vacina') | 
        Q(nome__icontains='Suplemento')
    )
    
    # Combina as duas queryset
    categorias = categorias_usuario.union(categorias_globais)
    
    unidades = UnidadeMedida.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'estoque/insumo_form.html', {
        'insumo': insumo,
        'categorias': categorias,
        'unidades': unidades
    })

@login_required
def insumo_delete(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk, usuario=request.user)
    
    # Verificar se existem movimentações relacionadas a este insumo
    movimentacoes = MovimentacaoEstoque.objects.filter(insumo=insumo)
    
    if movimentacoes.exists():
        messages.warning(request, f'Não é possível excluir este insumo porque existem {movimentacoes.count()} movimentações de estoque relacionadas a ele. Você pode desativá-lo em vez de excluí-lo.')
        # Redirecionar para a página de desativação em vez da lista
        return redirect('insumo_toggle_status', pk=insumo.pk)
        
    if request.method == 'POST':
        try:
            insumo.delete()
            messages.success(request, 'Insumo excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir insumo: {str(e)}')
        return redirect('estoque_list')
    
    return render(request, 'estoque/insumo_delete.html', {'insumo': insumo})

@login_required
def insumo_toggle_status(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        # Inverte o status atual
        insumo.ativo = not insumo.ativo
        insumo.save()
        
        status = 'ativado' if insumo.ativo else 'desativado'
        messages.success(request, f'Insumo {status} com sucesso!')
        return redirect('estoque_list')
        
    return render(request, 'estoque/insumo_toggle_status.html', {
        'insumo': insumo,
        'acao': 'Ativar' if not insumo.ativo else 'Desativar'
    })

@login_required
def entrada_estoque(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                insumo = get_object_or_404(Insumo, id=request.POST['insumo'], usuario=request.user)
                quantidade = Decimal(request.POST['quantidade'])
                valor_unitario = Decimal(request.POST['valor_unitario'])

                # Cria a movimentação
                MovimentacaoEstoque.objects.create(
                    insumo=insumo,
                    tipo='E',
                    data=request.POST['data'],
                    quantidade=quantidade,
                    valor_unitario=valor_unitario,
                    destino_id=request.POST['fazenda'],
                    observacao=request.POST.get('observacao', ''),
                    usuario=request.user
                )

                messages.success(request, 'Entrada de estoque registrada com sucesso!')
                return redirect('estoque_list')

        except Exception as e:
            messages.error(request, f'Erro ao registrar entrada: {str(e)}')
            return redirect('entrada_estoque')

    else:
        insumos = Insumo.objects.filter(usuario=request.user)
        fazendas = Fazenda.objects.filter(usuario=request.user)
        return render(request, 'estoque/entrada_form.html', {
            'insumos': insumos,
            'fazendas': fazendas
        })

@login_required
def saida_estoque(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                insumo = get_object_or_404(Insumo, id=request.POST['insumo'], usuario=request.user)
                quantidade = Decimal(request.POST['quantidade'].replace(',', '.'))
                lote = get_object_or_404(Lote, id=request.POST['destino'], fazenda__usuario=request.user)
                
                # Verifica se há saldo suficiente
                if quantidade > insumo.saldo_estoque:
                    messages.error(request, 'Quantidade maior que o saldo disponível.')
                    return redirect('saida_estoque')

                # Cria a movimentação
                movimentacao = MovimentacaoEstoque.objects.create(
                    insumo=insumo,
                    tipo='S',
                    data=request.POST['data'],
                    quantidade=quantidade,
                    valor_unitario=insumo.preco_medio,
                    destino_lote=lote,
                    observacao=request.POST.get('observacao', ''),
                    usuario=request.user
                )

                # Faz o rateio entre os animais ativos do lote
                animais_ativos = Animal.objects.filter(
                    lote=lote,
                    situacao='ATIVO'
                ).select_for_update()
                
                num_animais = animais_ativos.count()
                
                if num_animais > 0:
                    valor_por_animal = movimentacao.valor_total / num_animais
                    
                    # Cria o rateio e atualiza o custo variável de cada animal
                    for animal in animais_ativos:
                        # Cria o rateio
                        RateioMovimentacao.objects.create(
                            movimentacao=movimentacao,
                            animal=animal,
                            valor=valor_por_animal
                        )

                        # Atualiza o custo variável do animal
                        animal.custo_variavel += valor_por_animal
                        animal.save(update_fields=['custo_variavel'])

                messages.success(request, 'Saída de estoque registrada com sucesso!')
                return redirect('saida_list')

        except Exception as e:
            messages.error(request, f'Erro ao registrar saída: {str(e)}')
            return redirect('saida_estoque')

    else:
        insumos = Insumo.objects.filter(
            usuario=request.user,
            saldo_estoque__gt=0
        ).select_related('unidade_medida')

        # Pegando os lotes com seus respectivos pastos atuais
        lotes = Lote.objects.filter(
            fazenda__usuario=request.user
        ).select_related('fazenda')
        
        # Para cada lote, pegamos as informações necessárias
        destinos = []
        for lote in lotes:
            animais_ativos = Animal.objects.filter(lote=lote, situacao='ATIVO')
            qtd_animais = animais_ativos.count()
            pasto_atual = None
            if qtd_animais > 0:
                animal = animais_ativos.first()
                pasto_atual = animal.pasto_atual.id_pasto if animal.pasto_atual else "Sem pasto"
            
            destinos.append({
                'id': lote.id,
                'id_lote': lote.id_lote,
                'pasto': pasto_atual,
                'fazenda': lote.fazenda.nome,
                'qtd_animais': qtd_animais
            })
        
        return render(request, 'estoque/saida_form.html', {
            'insumos': insumos,
            'destinos': destinos
        })

@login_required
def saida_nutricao_estoque(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                insumo = get_object_or_404(Insumo, id=request.POST['insumo'], usuario=request.user)
                lote = get_object_or_404(Lote, id=request.POST['lote'], usuario=request.user)
                
                quantidade = Decimal(request.POST['quantidade'].replace(',', '.'))
                consumo_pv = Decimal(request.POST['consumo_pv'].replace(',', '.')) if request.POST.get('consumo_pv') else None

                if quantidade > insumo.saldo_estoque:
                    messages.error(request, 'Quantidade maior que o saldo disponível.')
                    return redirect('saida_nutricao_estoque')

                # Cria a movimentação
                movimentacao = MovimentacaoEstoque.objects.create(
                    tipo='SN',
                    insumo=insumo,
                    destino_lote=lote,
                    quantidade=quantidade,
                    valor_unitario=insumo.preco_medio,
                    data=request.POST['data'],
                    observacao=request.POST.get('observacao', ''),
                    usuario=request.user,
                    consumo_pv=consumo_pv
                )

                # Faz o rateio entre os animais ativos do lote
                animais_ativos = Animal.objects.filter(
                    lote=lote,
                    situacao='ATIVO'
                ).select_for_update()
                
                num_animais = animais_ativos.count()
                
                if num_animais > 0:
                    valor_por_animal = movimentacao.valor_total / num_animais
                    
                    # Cria o rateio e atualiza o custo variável de cada animal
                    for animal in animais_ativos:
                        # Cria o rateio
                        RateioMovimentacao.objects.create(
                            movimentacao=movimentacao,
                            animal=animal,
                            valor=valor_por_animal
                        )

                        # Atualiza o custo variável do animal
                        animal.custo_variavel += valor_por_animal
                        animal.save(update_fields=['custo_variavel'])

                messages.success(request, 'Saída de nutrição registrada com sucesso!')
                return redirect('saida_nutricao_list')

        except Exception as e:
            messages.error(request, f'Erro ao registrar saída: {str(e)}')
            return redirect('saida_nutricao_estoque')

    else:
        # Carrega insumos com saldo disponível
        insumos = Insumo.objects.filter(
            usuario=request.user,
            saldo_estoque__gt=0
        ).select_related('unidade_medida')

        # Otimização: Pré-calcular os pesos médios e GMDs por lote
        from django.db.models import Avg, F, Q, Count, Case, When, Value, DecimalField
        from django.db.models.functions import Coalesce
        
        # Buscar todos os lotes do usuário
        lotes = Lote.objects.filter(
            fazenda__usuario=request.user
        ).select_related('fazenda')
        
        # Preparar informações dos lotes de forma mais eficiente
        lote_ids = [lote.id for lote in lotes]
        
        # Busca todos os animais ativos dos lotes em uma única consulta
        animais_por_lote = {}
        animais_query = Animal.objects.filter(
            lote_id__in=lote_ids, 
            situacao='ATIVO'
        ).select_related('lote')
        
        for animal in animais_query:
            if animal.lote_id not in animais_por_lote:
                animais_por_lote[animal.lote_id] = []
            animais_por_lote[animal.lote_id].append(animal)
        
        # Busca a última pesagem de cada animal em uma única consulta
        animal_ids = [animal.id for animals in animais_por_lote.values() for animal in animals]
        
        # Subquery para obter apenas a última pesagem de cada animal
        from django.db.models import OuterRef, Subquery, Max
        
        ultima_data_pesagem_subquery = Pesagem.objects.filter(
            animal=OuterRef('animal')
        ).values('animal').annotate(
            max_data=Max('data')
        ).values('max_data')[:1]
        
        ultimas_pesagens = Pesagem.objects.filter(
            animal_id__in=animal_ids
        ).annotate(
            is_latest=Subquery(ultima_data_pesagem_subquery)
        ).filter(
            data=F('is_latest')
        ).select_related('animal')
        
        # Mapeia as últimas pesagens por animal_id para acesso rápido
        pesagens_por_animal = {p.animal_id: p for p in ultimas_pesagens}
        
        # Processa os lotes com os dados pré-carregados
        lotes_data = []
        for lote in lotes:
            # Obtém os animais deste lote
            animais_lote = animais_por_lote.get(lote.id, [])
            quantidade_atual = len(animais_lote)
            
            # Calcula o peso médio usando as pesagens pré-carregadas
            peso_total = 0
            animais_com_peso = 0
            
            for animal in animais_lote:
                # Usa a última pesagem pré-carregada ou o peso de entrada
                if animal.id in pesagens_por_animal:
                    peso_total += pesagens_por_animal[animal.id].peso
                    animais_com_peso += 1
                elif animal.peso_entrada:
                    peso_total += animal.peso_entrada
                    animais_com_peso += 1
            
            # Calcula as médias com proteção contra divisão por zero
            peso_medio = peso_total / animais_com_peso if animais_com_peso > 0 else 0
            
            # Simplificação: usamos um valor padrão para GMD para evitar cálculos pesados
            # Em uma implementação completa, poderíamos pré-calcular GMDs periodicamente
            gmd_medio = 0
            
            lotes_data.append({
                'lote': lote,
                'quantidade_atual': quantidade_atual,
                'peso_medio': peso_medio,
                'gmd_medio': gmd_medio
            })
        
        return render(request, 'estoque/saida_nutricao_form.html', {
            'insumos': insumos,
            'lotes_info': lotes_data
        })

@login_required
def saida_list(request):
    saidas = MovimentacaoEstoque.objects.filter(
        usuario=request.user,
        tipo='S'
    ).select_related('insumo', 'destino_lote', 'destino_lote__fazenda')
    
    return render(request, 'estoque/saida_list.html', {
        'saidas': saidas
    })

class SaidaNutricaoListView(ListView):
    model = MovimentacaoEstoque
    template_name = 'estoque/saida_nutricao_list.html'
    context_object_name = 'saidas'
    
    def get_queryset(self):
        return MovimentacaoEstoque.objects.filter(tipo='SN').order_by('-data')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Para cada saída, adiciona os dados calculados do lote
        saidas_data = []
        for saida in context['saidas']:
            try:
                if saida.destino_lote:
                    lote = saida.destino_lote
                    # Calcula a quantidade atual de animais
                    quantidade_atual = Animal.objects.filter(
                        lote=lote,
                        situacao='ATIVO'
                    ).count()
                    
                    # Calcula o peso médio e GMD do lote
                    animais = Animal.objects.filter(lote=lote, situacao='ATIVO')
                    
                    pesos = []
                    
                    for animal in animais:
                        # Pega a última pesagem para o peso médio
                        ultima_pesagem = animal.pesagens.order_by('-data').first()
                        if ultima_pesagem:
                            pesos.append(ultima_pesagem.peso)
                        
                    # Calcula as médias com proteção contra divisão por zero
                    peso_medio = sum(pesos) / len(pesos) if pesos else 0
                    
                    # Adiciona os dados calculados ao lote
                    lote.peso_medio = peso_medio
                    lote.gmd_medio = 0.8  # Valor padrão razoável para GMD
                    saidas_data.append(saida)
            except Exception as e:
                print(f"Erro ao processar saída {saida.id}: {str(e)}")
                saidas_data.append(saida)
                continue
            
        context['saidas'] = saidas_data
        return context

@login_required
def get_pasto_lote(request):
    """Retorna o pasto atual de um lote"""
    lote_id = request.GET.get('lote_id')
    try:
        lote = Lote.objects.get(id=lote_id, fazenda__usuario=request.user)
        return JsonResponse({
            'pasto_id': lote.pasto_atual_id if lote.pasto_atual_id else None
        })
    except Lote.DoesNotExist:
        return JsonResponse({'error': 'Lote não encontrado'}, status=404)

@login_required
def get_subcategorias(request):
    categoria_id = request.GET.get('categoria_id')
    subcategorias = SubcategoriaCusto.objects.filter(categoria_id=categoria_id)
    return JsonResponse(list(subcategorias.values('id', 'nome')), safe=False)

@login_required
def get_insumo_info(request):
    insumo_id = request.GET.get('insumo_id')
    insumo = get_object_or_404(Insumo, id=insumo_id, usuario=request.user)
    return JsonResponse({
        'unidade_medida': insumo.unidade_medida.sigla,
        'saldo_atual': float(insumo.saldo_estoque),
        'preco_medio': float(insumo.preco_medio)
    })

@login_required
def unidade_medida_create(request):
    if request.method == 'POST':
        try:
            unidade = UnidadeMedida(
                nome=request.POST['nome'],
                sigla=request.POST['sigla'],
                tipo=request.POST['tipo'],
                descricao=request.POST.get('descricao', ''),
                usuario=request.user
            )
            unidade.save()
            messages.success(request, 'Unidade de medida criada com sucesso!')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            messages.error(request, f'Erro ao criar unidade de medida: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return render(request, 'estoque/unidade_medida_form.html')

@login_required
def unidade_medida_edit(request, pk):
    unidade = get_object_or_404(UnidadeMedida, pk=pk, usuario=request.user)
    if request.method == 'POST':
        try:
            unidade.nome = request.POST['nome']
            unidade.sigla = request.POST['sigla']
            unidade.tipo = request.POST['tipo']
            unidade.descricao = request.POST.get('descricao', '')
            unidade.save()
            messages.success(request, 'Unidade de medida atualizada com sucesso!')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            messages.error(request, f'Erro ao atualizar unidade de medida: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return render(request, 'estoque/unidade_medida_form.html', {'unidade': unidade})

@login_required
def entrada_list(request):
    # Busca todas as entradas do usuário
    entradas = MovimentacaoEstoque.objects.filter(
        usuario=request.user,
        tipo='E'
    ).select_related('insumo').order_by('-data')
    
    # Calcula o valor total das entradas
    total_valor_entradas = sum(entrada.valor_total for entrada in entradas)
    
    # Obtém a data atual e calcula o primeiro dia do mês atual
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Filtra entradas do mês atual
    entradas_mes_atual = entradas.filter(data__gte=primeiro_dia_mes).count()
    
    # Conta quantos insumos diferentes têm entradas
    insumos_com_entrada = set()
    for entrada in entradas:
        if entrada.insumo_id:
            insumos_com_entrada.add(entrada.insumo_id)
    total_insumos_entrada = len(insumos_com_entrada)
    
    return render(request, 'estoque/entrada_list.html', {
        'entradas': entradas,
        'total_valor_entradas': total_valor_entradas,
        'entradas_mes_atual': entradas_mes_atual,
        'total_insumos_entrada': total_insumos_entrada
    })

@login_required
def entrada_edit(request, pk):
    entrada = get_object_or_404(MovimentacaoEstoque, pk=pk, usuario=request.user, tipo='E')
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Reverte a entrada antiga
                entrada.insumo.reverter_movimentacao(entrada)
                
                # Atualiza os dados
                entrada.insumo_id = request.POST['insumo']
                entrada.data = request.POST['data']
                entrada.quantidade = Decimal(request.POST['quantidade'])
                entrada.valor_unitario = Decimal(request.POST['valor_unitario'])
                entrada.destino_id = request.POST['fazenda']
                entrada.observacao = request.POST.get('observacao', '')
                entrada.save()
                
                # Processa a nova entrada
                entrada.insumo.processar_movimentacao(entrada)
                
                messages.success(request, 'Entrada atualizada com sucesso!')
                return redirect('entrada_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar entrada: {str(e)}')
    
    insumos = Insumo.objects.filter(usuario=request.user)
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'estoque/entrada_form.html', {
        'entrada': entrada,
        'insumos': insumos,
        'fazendas': fazendas
    })

@login_required
def entrada_delete(request, pk):
    entrada = get_object_or_404(MovimentacaoEstoque, pk=pk, usuario=request.user, tipo='E')
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Reverte a entrada
                entrada.insumo.reverter_movimentacao(entrada)
                entrada.delete()
                messages.success(request, 'Entrada excluída com sucesso!')
                return redirect('entrada_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir entrada: {str(e)}')
    return render(request, 'estoque/entrada_delete.html', {'entrada': entrada})

@login_required
def saida_nutricao_list(request):
    saidas = MovimentacaoEstoque.objects.filter(
        usuario=request.user,
        tipo='SN'
    ).select_related('insumo', 'destino_lote', 'destino_lote__fazenda')
    
    return render(request, 'estoque/saida_nutricao_list.html', {
        'saidas': saidas
    })

class SaidaNutricaoCreateView(CreateView):
    model = MovimentacaoEstoque
    template_name = 'estoque/saida_nutricao_form.html'
    fields = ['insumo', 'data', 'quantidade', 'observacao']
    success_url = reverse_lazy('saida_nutricao_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.user.id
        
        # Tenta obter dados do cache primeiro
        cache_key = f'saida_nutricao_form_data_{user_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
            return context
        
        # Se não estiver em cache, busca os dados normalmente
        # Busca apenas insumos ativos com saldo positivo - otimização 1
        insumos = Insumo.objects.filter(
            usuario=self.request.user,
            ativo=True,
            saldo_estoque__gt=0
        ).select_related('unidade_medida')
        
        # Busca apenas lotes da fazenda do usuário - otimização 2
        lotes = Lote.objects.filter(
            usuario=self.request.user
        ).select_related('fazenda')
        
        # Pré-carrega os dados de animais e pesagens para todos os lotes de uma vez - otimização 3
        lote_ids = [lote.id for lote in lotes]
        
        # Busca todos os animais ativos dos lotes em uma única consulta
        animais_por_lote = {}
        animais_query = Animal.objects.filter(
            lote_id__in=lote_ids, 
            situacao='ATIVO'
        ).select_related('lote')
        
        for animal in animais_query:
            if animal.lote_id not in animais_por_lote:
                animais_por_lote[animal.lote_id] = []
            animais_por_lote[animal.lote_id].append(animal)
        
        # Busca a última pesagem de cada animal em uma única consulta
        animal_ids = [animal.id for animals in animais_por_lote.values() for animal in animals]
        
        # Subquery para obter apenas a última pesagem de cada animal
        from django.db.models import OuterRef, Subquery, Max
        
        ultima_pesagem_subquery = Pesagem.objects.filter(
            animal=OuterRef('animal')
        ).order_by('-data').values('data')[:1]
        
        ultimas_pesagens = Pesagem.objects.filter(
            animal_id__in=animal_ids
        ).annotate(
            is_latest=Subquery(ultima_pesagem_subquery)
        ).filter(
            data=F('is_latest')
        ).select_related('animal')
        
        # Mapeia as últimas pesagens por animal_id para acesso rápido
        pesagens_por_animal = {p.animal_id: p for p in ultimas_pesagens}
        
        # Processa os lotes com os dados pré-carregados
        lotes_data = []
        for lote in lotes:
            # Obtém os animais deste lote
            animais_lote = animais_por_lote.get(lote.id, [])
            quantidade_atual = len(animais_lote)
            
            # Calcula o peso médio usando as pesagens pré-carregadas
            peso_total = 0
            animais_com_peso = 0
            
            for animal in animais_lote:
                # Usa a última pesagem pré-carregada ou o peso de entrada
                if animal.id in pesagens_por_animal:
                    peso_total += pesagens_por_animal[animal.id].peso
                    animais_com_peso += 1
                elif animal.peso_entrada:
                    peso_total += animal.peso_entrada
                    animais_com_peso += 1
            
            # Calcula as médias com proteção contra divisão por zero
            peso_medio = peso_total / animais_com_peso if animais_com_peso > 0 else 0
            
            # Simplificação: usamos um valor padrão para GMD para evitar cálculos pesados
            # Em uma implementação completa, poderíamos pré-calcular GMDs periodicamente
            gmd_medio = 0
            
            lotes_data.append({
                'lote': lote,
                'quantidade_atual': quantidade_atual,
                'peso_medio': peso_medio,
                'gmd_medio': gmd_medio
            })
        
        # Armazena os dados no contexto
        context_data = {
            'insumos': insumos,
            'lotes': lotes_data
        }
        
        # Salva no cache por 10 minutos
        cache.set(cache_key, context_data, 60 * 10)
        
        # Atualiza o contexto
        context.update(context_data)
        return context
        
    def form_valid(self, form):
        try:
            form.instance.tipo = 'SN'
            form.instance.destino_lote_id = self.request.POST.get('lote')
            form.instance.consumo_pv = self.request.POST.get('consumo_pv')
            form.instance.usuario = self.request.user
            response = super().form_valid(form)
            
            # Invalida o cache após uma nova saída ser criada
            cache_key = f'saida_nutricao_form_data_{self.request.user.id}'
            cache.delete(cache_key)
            
            messages.success(self.request, 'Saída de nutrição registrada com sucesso!')
            return response
        except Exception as e:
            print(f"Erro ao salvar saída de nutrição: {str(e)}")
            messages.error(self.request, 'Erro ao registrar saída')
            return self.form_invalid(form)

class SaidaNutricaoView(ListView):
    model = MovimentacaoEstoque
    template_name = 'estoque/saida_nutricao_list.html'
    context_object_name = 'saidas'
    
    def get_queryset(self):
        # Otimização: Usar select_related para carregar dados relacionados em uma única consulta
        return MovimentacaoEstoque.objects.filter(
            usuario=self.request.user,
            tipo='SN'
        ).select_related('insumo', 'destino_lote').order_by('-data')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.user.id
        
        # Tenta obter dados do cache primeiro
        cache_key = f'saida_nutricao_list_data_{user_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
            return context
        
        # Se não estiver em cache, busca os dados normalmente
        # Otimização: Filtrar insumos ativos e com saldo positivo
        insumos = Insumo.objects.filter(
            usuario=self.request.user,
            ativo=True
        ).select_related('unidade_medida')
        
        # Otimização: Filtrar lotes do usuário e usar select_related
        lotes = Lote.objects.filter(
            usuario=self.request.user
        ).select_related('fazenda')
        
        # Pré-carrega os dados de animais e pesagens para todos os lotes de uma vez
        lote_ids = [lote.id for lote in lotes]
        
        # Busca todos os animais ativos dos lotes em uma única consulta
        animais_por_lote = {}
        animais_query = Animal.objects.filter(
            lote_id__in=lote_ids, 
            situacao='ATIVO'
        ).select_related('lote')
        
        for animal in animais_query:
            if animal.lote_id not in animais_por_lote:
                animais_por_lote[animal.lote_id] = []
            animais_por_lote[animal.lote_id].append(animal)
        
        # Busca a última pesagem de cada animal em uma única consulta
        animal_ids = [animal.id for animals in animais_por_lote.values() for animal in animals]
        
        # Subquery para obter apenas a última pesagem de cada animal
        ultima_pesagem_subquery = Pesagem.objects.filter(
            animal=OuterRef('animal')
        ).order_by('-data').values('data')[:1]
        
        ultimas_pesagens = Pesagem.objects.filter(
            animal_id__in=animal_ids
        ).annotate(
            is_latest=Subquery(ultima_pesagem_subquery)
        ).filter(
            data=F('is_latest')
        ).select_related('animal')
        
        # Mapeia as últimas pesagens por animal_id para acesso rápido
        pesagens_por_animal = {p.animal_id: p for p in ultimas_pesagens}
        
        # Processa os lotes com os dados pré-carregados
        lotes_data = []
        for lote in lotes:
            # Obtém os animais deste lote
            animais_lote = animais_por_lote.get(lote.id, [])
            quantidade_atual = len(animais_lote)
            
            # Calcula o peso médio usando as pesagens pré-carregadas
            peso_total = 0
            animais_com_peso = 0
            
            for animal in animais_lote:
                # Usa a última pesagem pré-carregada ou o peso de entrada
                if animal.id in pesagens_por_animal:
                    peso_total += pesagens_por_animal[animal.id].peso
                    animais_com_peso += 1
                elif animal.peso_entrada:
                    peso_total += animal.peso_entrada
                    animais_com_peso += 1
            
            # Calcula as médias com proteção contra divisão por zero
            peso_medio = peso_total / animais_com_peso if animais_com_peso > 0 else 0
            
            # Atualiza o lote com os valores calculados
            lote.peso_medio = peso_medio
            lote.quantidade_atual = quantidade_atual
            lotes_data.append(lote)
        
        # Armazena os dados no contexto
        context_data = {
            'insumos': insumos,
            'lotes': lotes_data
        }
        
        # Salva no cache por 10 minutos
        cache.set(cache_key, context_data, 60 * 10)
        
        # Atualiza o contexto
        context.update(context_data)
        return context

@login_required
def saida_nutricao_detail(request, pk):
    # Tenta obter dados do cache primeiro
    cache_key = f'saida_nutricao_detail_{pk}_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, 'estoque/saida_nutricao_detail.html', cached_data)
    
    # Otimização: Usar select_related para carregar dados relacionados em uma única consulta
    saida = get_object_or_404(
        MovimentacaoEstoque.objects.select_related('insumo', 'destino_lote', 'usuario'),
        pk=pk, 
        tipo='SN', 
        usuario=request.user
    )
    
    context = {'saida': saida}
    
    # Calcula estatísticas do lote na data da movimentação
    lote = saida.destino_lote
    if lote:
        # Otimização: Usar select_related para reduzir o número de consultas
        # Busca animais que estavam no lote na data da movimentação
        animais = Animal.objects.filter(
            lote=lote,
            data_entrada__lte=saida.data
        ).exclude(
            data_saida__lt=saida.data  # Exclui apenas animais que saíram antes da data da movimentação
        ).select_related('categoria_animal', 'raca')
        
        # Otimização: Buscar todas as pesagens relevantes em uma única consulta
        animal_ids = [animal.id for animal in animais]
        
        # Subquery para obter apenas a última pesagem de cada animal antes da data da saída
        from django.db.models import OuterRef, Subquery, Max
        
        ultima_data_pesagem_subquery = Pesagem.objects.filter(
            animal=OuterRef('animal'),
            data__lte=saida.data
        ).values('animal').annotate(
            max_data=Max('data')
        ).values('max_data')[:1]
        
        ultimas_pesagens = Pesagem.objects.filter(
            animal_id__in=animal_ids,
            data__lte=saida.data
        ).annotate(
            is_latest=Subquery(ultima_data_pesagem_subquery)
        ).filter(
            data=F('is_latest')
        )
        
        # Mapeia as pesagens por animal_id para acesso rápido
        pesagens_por_animal = {p.animal_id: p for p in ultimas_pesagens}
        
        peso_total = 0
        count = 0
        animais_com_peso = []
        
        for animal in animais:
            # Verifica se temos a última pesagem deste animal
            if animal.id in pesagens_por_animal:
                peso = pesagens_por_animal[animal.id].peso
                peso_total += peso
                count += 1
                animais_com_peso.append({
                    'animal': animal,
                    'peso': peso
                })
            # Se não tiver pesagem, tenta usar o peso de entrada
            elif animal.peso_entrada and animal.data_entrada <= saida.data:
                peso_total += animal.peso_entrada
                count += 1
                animais_com_peso.append({
                    'animal': animal,
                    'peso': animal.peso_entrada
                })
        
        peso_medio = peso_total / count if count > 0 else 0
        
        # Calcula o consumo diário do lote
        consumo_diario_lote = peso_medio * count * (saida.consumo_pv / 100) if count > 0 and saida.consumo_pv else 0
        
        # Calcula o consumo por cabeça
        consumo_por_cabeca = saida.quantidade / count if count > 0 else 0
        
        # Calcula o consumo em % do peso vivo
        consumo_pv_calculado = (consumo_por_cabeca / peso_medio) * 100 if peso_medio > 0 else 0
        
        # Adiciona os dados calculados ao contexto
        context.update({
            'lote': lote,
            'animais': animais,
            'animais_com_peso': animais_com_peso,
            'count': count,
            'peso_medio': peso_medio,
            'consumo_diario_lote': consumo_diario_lote,
            'consumo_por_cabeca': consumo_por_cabeca,
            'consumo_pv_calculado': consumo_pv_calculado
        })
    
    # Salva no cache por 30 minutos
    cache.set(cache_key, context, 60 * 30)
    
    return render(request, 'estoque/saida_nutricao_detail.html', context)

@login_required
def saida_edit(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='S', usuario=request.user)
    if request.method == 'POST':
        try:
            insumo = get_object_or_404(Insumo, id=request.POST['insumo'], usuario=request.user)
            lote = get_object_or_404(Lote, id=request.POST['lote'], usuario=request.user)
            quantidade = Decimal(request.POST['quantidade'].replace(',', '.'))

            if quantidade > insumo.saldo_estoque + saida.quantidade:
                messages.error(request, 'Quantidade maior que o saldo disponível.')
                return redirect('saida_edit', pk=pk)

            saida.insumo = insumo
            saida.destino_lote = lote
            saida.quantidade = quantidade
            saida.data = request.POST['data']
            saida.observacao = request.POST.get('observacao', '')
            saida.save()

            messages.success(request, 'Saída atualizada com sucesso!')
            return redirect('saida_list')

        except Exception as e:
            messages.error(request, f'Erro ao atualizar saída: {str(e)}')

    insumos = Insumo.objects.filter(
        usuario=request.user,
        saldo_estoque__gt=0
    ).select_related('unidade_medida')

    lotes = Lote.objects.filter(
        usuario=request.user,
        situacao='A'
    ).select_related('fazenda')

    return render(request, 'estoque/saida_form.html', {
        'saida': saida,
        'insumos': insumos,
        'lotes': lotes
    })

@login_required
def saida_delete(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='S', usuario=request.user)
    if request.method == 'POST':
        saida.delete()
        messages.success(request, 'Saída excluída com sucesso!')
        return redirect('saida_list')
    return render(request, 'estoque/saida_delete.html', {'saida': saida})

@login_required
def saida_nutricao_edit(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='SN', usuario=request.user)
    if request.method == 'POST':
        try:
            insumo = get_object_or_404(Insumo, id=request.POST['insumo'], usuario=request.user)
            lote = get_object_or_404(Lote, id=request.POST['lote'], usuario=request.user)
            
            quantidade = Decimal(request.POST['quantidade'].replace(',', '.'))
            consumo_pv = Decimal(request.POST['consumo_pv'].replace(',', '.')) if request.POST.get('consumo_pv') else None

            if quantidade > insumo.saldo_estoque + saida.quantidade:
                messages.error(request, 'Quantidade maior que o saldo disponível.')
                return redirect('saida_nutricao_edit', pk=pk)

            # Exclui os rateios antigos
            RateioMovimentacao.objects.filter(movimentacao=saida).delete()

            # Atualiza a saída
            saida.insumo = insumo
            saida.destino_lote = lote
            saida.quantidade = quantidade
            saida.data = request.POST['data']
            saida.observacao = request.POST.get('observacao', '')
            saida.consumo_pv = consumo_pv
            saida.save()

            # Cria novos rateios
            animais_ativos = lote.animal_set.filter(situacao='ATIVO')
            if animais_ativos.exists():
                valor_por_animal = saida.valor_total / animais_ativos.count()
                for animal in animais_ativos:
                    # Cria o rateio
                    RateioMovimentacao.objects.create(
                        movimentacao=saida,
                        animal=animal,
                        valor=valor_por_animal
                    )

            messages.success(request, 'Saída de nutrição atualizada com sucesso!')
            return redirect('saida_nutricao_list')

        except Exception as e:
            messages.error(request, f'Erro ao atualizar saída: {str(e)}')

    insumos = Insumo.objects.filter(
        usuario=request.user,
        saldo_estoque__gt=0
    ).select_related('unidade_medida')

    lotes = Lote.objects.filter(
        usuario=request.user
    ).select_related('fazenda')

    return render(request, 'estoque/saida_nutricao_form.html', {
        'saida': saida,
        'insumos': insumos,
        'lotes': lotes
    })

@login_required
def saida_nutricao_delete(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='SN', usuario=request.user)
    if request.method == 'POST':
        saida.delete()
        messages.success(request, 'Saída de nutrição excluída com sucesso!')
        return redirect('saida_nutricao_list')
    return render(request, 'estoque/saida_nutricao_delete.html', {'saida': saida})

# Função para ser chamada quando uma despesa com alocação 'estoque' for salva
def criar_entrada_estoque_from_despesa(despesa, item_despesa, insumo):
    """
    Cria uma entrada de estoque a partir de uma despesa.
    
    Args:
        despesa: Objeto Despesa
        item_despesa: Objeto ItemDespesa
        insumo: Objeto Insumo
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Verifica se a categoria é do tipo estoque usando a função utilitária
    if not is_categoria_estoque(item_despesa.categoria):
        logger.warning(f"Categoria {item_despesa.categoria.nome} não é do tipo estoque. Alocação: {item_despesa.categoria.alocacao}")
        return
    
    # Log detalhado para depuração
    logger.info(f"Criando entrada de estoque para despesa {despesa.id}, item {item_despesa.id}, insumo {insumo.nome}")
    logger.info(f"Categoria: {item_despesa.categoria.nome} (ID: {item_despesa.categoria.id}, Alocação: {item_despesa.categoria.alocacao}")
    logger.info(f"Usuário da categoria: {item_despesa.categoria.usuario_id if item_despesa.categoria.usuario_id else 'Global'}")
    
    # Verifica se há uma fazenda de destino
    if not item_despesa.fazenda_destino:
        logger.warning(f"Item de despesa {item_despesa.id} não tem fazenda de destino definida")
        # Tenta definir automaticamente a fazenda de destino para categorias globais
        if not item_despesa.categoria.usuario_id:  # Se for categoria global
            logger.info("Categoria global detectada, tentando definir fazenda de destino automaticamente")
            try:
                from .models import Fazenda
                # Tenta encontrar qualquer fazenda do usuário
                qualquer_fazenda = Fazenda.objects.filter(usuario=despesa.usuario).first()
                if qualquer_fazenda:
                    item_despesa.fazenda_destino = qualquer_fazenda
                    item_despesa.save()
                    logger.info(f"Fazenda de destino definida automaticamente: {qualquer_fazenda.nome} (ID: {qualquer_fazenda.id})")
                else:
                    logger.warning("Não foi possível definir automaticamente a fazenda de destino")
            except Exception as e:
                logger.error(f"Erro ao tentar definir fazenda de destino automaticamente: {str(e)}")
                # Continua mesmo sem fazenda de destino para categorias globais
                logger.info("Categoria global detectada, continuando mesmo sem fazenda de destino")
        else:
            # Para categorias do usuário, ainda exigimos a fazenda de destino
            logger.error("Categoria do usuário requer fazenda de destino, abortando criação de entrada de estoque")
            return
    else:
        logger.info(f"Fazenda de destino: {item_despesa.fazenda_destino.nome} (ID: {item_despesa.fazenda_destino.id})")
    
    try:
        # Determina a fazenda de origem a partir do item_despesa.fazenda_destino
        fazenda_origem = None
        if item_despesa.fazenda_destino:
            fazenda_origem = item_despesa.fazenda_destino
            logger.info(f"Fazenda de origem definida a partir do item_despesa.fazenda_destino: {fazenda_origem.nome} (ID: {fazenda_origem.id})")
        
        # Cria a movimentação de estoque
        movimentacao = MovimentacaoEstoque.objects.create(
            insumo=insumo,
            tipo='E',
            data=despesa.data_emissao,
            quantidade=item_despesa.quantidade,
            valor_unitario=item_despesa.valor_unitario,
            valor_total=item_despesa.valor_total,
            despesa=despesa,
            fazenda_origem=fazenda_origem,  # Define a fazenda de origem
            usuario=despesa.usuario
        )
        
        # Não atualizamos o saldo e preço médio do insumo aqui, pois isso já é feito no método save() da classe MovimentacaoEstoque
        
        logger.info(f"Entrada de estoque criada: ID {movimentacao.id} para insumo {insumo.nome}")
        logger.info(f"Insumo atualizado: saldo={insumo.saldo_estoque}, preço médio={insumo.preco_medio}, valor total={insumo.valor_total}")
        
        # Registra a fazenda de destino, se houver
        if item_despesa.fazenda_destino:
            logger.info(f"Fazenda de destino: {item_despesa.fazenda_destino.nome}")
        else:
            logger.info("Sem fazenda de destino definida (categoria global)")
        
        return movimentacao
    except Exception as e:
        logger.error(f"Erro ao criar entrada de estoque: {str(e)}")
        return None

@login_required
def entrada_detail(request, pk):
    entrada = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='E', usuario=request.user)
    return render(request, 'estoque/entrada_detail.html', {
        'entrada': entrada
    })

@login_required
def saida_detail(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='S', usuario=request.user)
    return render(request, 'estoque/saida_detail.html', {
        'saida': saida
    })
