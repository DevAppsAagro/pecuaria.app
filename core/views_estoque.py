from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models_estoque import Insumo, MovimentacaoEstoque, RateioMovimentacao
from .models import (
    Lote, Animal, Fazenda, CategoriaCusto, SubcategoriaCusto, 
    UnidadeMedida, Pesagem
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from decimal import Decimal
from django.db.models import Subquery, OuterRef, Avg

@login_required
def estoque_list(request):
    insumos = Insumo.objects.filter(usuario=request.user)
    return render(request, 'estoque/estoque_list.html', {
        'insumos': insumos
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
    
    categorias = CategoriaCusto.objects.filter(alocacao='estoque')
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
    
    categorias = CategoriaCusto.objects.filter(alocacao='estoque')
    unidades = UnidadeMedida.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'estoque/insumo_form.html', {
        'insumo': insumo,
        'categorias': categorias,
        'unidades': unidades
    })

@login_required
def insumo_delete(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk, usuario=request.user)
    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo excluído com sucesso!')
        return redirect('estoque_list')
    return render(request, 'estoque/insumo_delete.html', {'insumo': insumo})

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
        insumos = Insumo.objects.filter(
            usuario=request.user,
            saldo_estoque__gt=0
        ).select_related('unidade_medida')

        # Pegando os lotes com suas informações
        lotes = Lote.objects.filter(
            fazenda__usuario=request.user
        ).select_related('fazenda')
        
        lotes_info = []
        for lote in lotes:
            animais_ativos = Animal.objects.filter(lote=lote, situacao='ATIVO')
            qtd_animais = animais_ativos.count()
            peso_medio = 0
            peso_total = 0
            gmd_medio = 0
            
            if qtd_animais > 0:
                # Calcula o peso médio e GMD dos animais ativos
                peso_total = 0
                gmd_total = 0
                animais_com_gmd = 0
                
                for animal in animais_ativos:
                    # Pega as duas últimas pesagens para calcular o GMD
                    ultimas_pesagens = animal.pesagens.order_by('-data')[:2]
                    if len(ultimas_pesagens) >= 2:
                        ultima_pesagem = ultimas_pesagens[0]
                        penultima_pesagem = ultimas_pesagens[1]
                        
                        # Calcula o GMD
                        dias = (ultima_pesagem.data - penultima_pesagem.data).days
                        if dias > 0:
                            gmd = (ultima_pesagem.peso - penultima_pesagem.peso) / dias
                            gmd_total += gmd
                            animais_com_gmd += 1
                    # Se tiver apenas uma pesagem, tenta calcular com o peso de entrada
                    elif len(ultimas_pesagens) == 1 and animal.peso_entrada and animal.data_entrada:
                        ultima_pesagem = ultimas_pesagens[0]
                        dias = (ultima_pesagem.data - animal.data_entrada).days
                        if dias > 0:
                            gmd = (ultima_pesagem.peso - animal.peso_entrada) / dias
                            gmd_total += gmd
                            animais_com_gmd += 1
                    
                    # Pega o último peso para a média de peso
                    ultima_pesagem = ultimas_pesagens[0] if ultimas_pesagens else None
                    if ultima_pesagem:
                        peso_total += ultima_pesagem.peso
                
                # Calcula as médias
                peso_medio = peso_total / qtd_animais if qtd_animais > 0 else 0
                gmd_medio = gmd_total / animais_com_gmd if animais_com_gmd > 0 else 0
            
            lotes_info.append({
                'lote': lote,
                'quantidade_atual': qtd_animais,
                'peso_medio': peso_medio,
                'gmd_medio': gmd_medio
            })
        
        return render(request, 'estoque/saida_nutricao_form.html', {
            'insumos': insumos,
            'lotes_info': lotes_info
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
                    gmds = []
                    
                    print("\n=== Iniciando cálculo de GMD para o lote ===")
                    
                    for animal in animais:
                        print(f"\nAnimal {animal.brinco_visual}:")
                        print(f"- Peso entrada: {animal.peso_entrada}kg")
                        print(f"- Data entrada: {animal.data_entrada}")
                        
                        # Busca todas as pesagens do animal
                        pesagens = list(Pesagem.objects.filter(
                            animal=animal
                        ).order_by('-data'))
                        
                        # Adiciona o peso de entrada como primeira pesagem se não estiver na lista
                        if animal.peso_entrada and animal.data_entrada:
                            peso_entrada_existe = any(
                                p.data == animal.data_entrada and abs(p.peso - animal.peso_entrada) < 0.01 
                                for p in pesagens
                            )
                            if not peso_entrada_existe:
                                peso_entrada = Pesagem(
                                    animal=animal,
                                    peso=animal.peso_entrada,
                                    data=animal.data_entrada,
                                    usuario=self.request.user
                                )
                                pesagens.append(peso_entrada)
                        
                        # Ordena todas as pesagens por data decrescente
                        pesagens.sort(key=lambda x: x.data, reverse=True)
                        
                        if pesagens:
                            ultima_pesagem = pesagens[0]
                            print(f"- Última pesagem: {ultima_pesagem.peso}kg em {ultima_pesagem.data}")
                            # Adiciona o último peso conhecido para média do lote
                            pesos.append(ultima_pesagem.peso)
                            
                            # Se tiver mais de uma pesagem, calcula o GMD entre as duas últimas
                            if len(pesagens) >= 2:
                                penultima_pesagem = pesagens[1]
                                dias = (ultima_pesagem.data - penultima_pesagem.data).days
                                print(f"- Dias entre pesagens: {dias}")
                                
                                if dias > 0:
                                    ganho = ultima_pesagem.peso - penultima_pesagem.peso
                                    gmd = round(ganho / dias, 2)
                                    print(f"- Ganho: {ganho}kg em {dias} dias")
                                    print(f"- GMD calculado: {gmd}kg/dia")
                                    
                                    if gmd > 0:  # Só considera GMDs positivos
                                        gmds.append(gmd)
                                        print(f"- GMD positivo, adicionado à média")
                                    else:
                                        print(f"- GMD negativo, ignorado")
                                else:
                                    print("- Dias = 0, não é possível calcular GMD")
                            elif len(pesagens) == 1 and animal.peso_entrada and animal.data_entrada:
                                dias = (ultima_pesagem.data - animal.data_entrada).days
                                if dias > 0:
                                    gmd = (ultima_pesagem.peso - animal.peso_entrada) / dias
                                    gmds.append(gmd)
                            else:
                                print("- Apenas uma pesagem disponível")
                        else:
                            print("- Sem pesagens registradas")
                            if animal.peso_entrada:
                                print(f"- Usando peso de entrada ({animal.peso_entrada}kg) para média")
                                # Se não tem pesagem, usa o peso de entrada para a média
                                pesos.append(animal.peso_entrada)
                
                # Calcula as médias com proteção contra divisão por zero
                peso_medio = sum(pesos) / len(pesos) if pesos else 0
                gmd_medio = sum(gmds) / len(gmds) if gmds else 0
                
                print(f"\nResultados do lote:")
                print(f"- Número de animais com GMD calculado: {len(gmds)}")
                if gmds:
                    print(f"- GMDs individuais: {[round(gmd, 2) for gmd in gmds]}")
                else:
                    print("- Nenhum GMD calculado")
                print(f"- Peso médio: {peso_medio:.2f}kg")
                print(f"- GMD médio: {gmd_medio:.2f}kg/dia")
                
                # Adiciona os dados calculados ao lote
                lote.peso_medio = peso_medio
                lote.gmd_medio = gmd_medio
                
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
    entradas = MovimentacaoEstoque.objects.filter(
        usuario=request.user,
        tipo='E'
    ).order_by('-data')
    return render(request, 'estoque/entrada_list.html', {
        'entradas': entradas
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
        context['insumos'] = Insumo.objects.all()
        
        # Busca os lotes e adiciona informações calculadas
        lotes = Lote.objects.all()
        lotes_data = []
        
        for lote in lotes:
            try:
                # Calcula a quantidade atual de animais
                animais = Animal.objects.filter(lote=lote, situacao='ATIVO')
                quantidade_atual = animais.count()
                
                # Calcula o peso médio e GMD do lote
                pesos = []
                gmds = []
                
                print(f"\n=== Iniciando cálculo de GMD para o lote {lote.id_lote} ===")
                print(f"Quantidade de animais: {quantidade_atual}")
                
                for animal in animais:
                    print(f"\nAnimal {animal.brinco_visual}:")
                    print(f"- Peso entrada: {animal.peso_entrada}kg")
                    print(f"- Data entrada: {animal.data_entrada}")
                    
                    # Busca todas as pesagens do animal
                    pesagens = list(Pesagem.objects.filter(
                        animal=animal
                    ).order_by('-data'))
                    
                    # Adiciona o peso de entrada como primeira pesagem se não estiver na lista
                    if animal.peso_entrada and animal.data_entrada:
                        peso_entrada_existe = any(
                            p.data == animal.data_entrada and abs(p.peso - animal.peso_entrada) < 0.01 
                            for p in pesagens
                        )
                        if not peso_entrada_existe:
                            peso_entrada = Pesagem(
                                animal=animal,
                                peso=animal.peso_entrada,
                                data=animal.data_entrada,
                                usuario=self.request.user
                            )
                            pesagens.append(peso_entrada)
                    
                    # Ordena todas as pesagens por data decrescente
                    pesagens.sort(key=lambda x: x.data, reverse=True)
                    
                    if pesagens:
                        ultima_pesagem = pesagens[0]
                        print(f"- Última pesagem: {ultima_pesagem.peso}kg em {ultima_pesagem.data}")
                        # Adiciona o último peso conhecido para média do lote
                        pesos.append(ultima_pesagem.peso)
                        
                        # Se tiver mais de uma pesagem, calcula o GMD entre as duas últimas
                        if len(pesagens) >= 2:
                            penultima_pesagem = pesagens[1]
                            dias = (ultima_pesagem.data - penultima_pesagem.data).days
                            print(f"- Dias entre pesagens: {dias}")
                            
                            if dias > 0:
                                ganho = ultima_pesagem.peso - penultima_pesagem.peso
                                gmd = round(ganho / dias, 2)
                                print(f"- Ganho: {ganho}kg em {dias} dias")
                                print(f"- GMD calculado: {gmd}kg/dia")
                                
                                if gmd > 0:  # Só considera GMDs positivos
                                    gmds.append(gmd)
                                    print(f"- GMD positivo, adicionado à média")
                                else:
                                    print(f"- GMD negativo, ignorado")
                            else:
                                print("- Dias = 0, não é possível calcular GMD")
                        elif len(pesagens) == 1 and animal.peso_entrada and animal.data_entrada:
                            dias = (ultima_pesagem.data - animal.data_entrada).days
                            if dias > 0:
                                gmd = (ultima_pesagem.peso - animal.peso_entrada) / dias
                                gmds.append(gmd)
                        else:
                            print("- Apenas uma pesagem disponível")
                    else:
                        print("- Sem pesagens registradas")
                        if animal.peso_entrada:
                            print(f"- Usando peso de entrada ({animal.peso_entrada}kg) para média")
                            # Se não tem pesagem, usa o peso de entrada para a média
                            pesos.append(animal.peso_entrada)
                
                # Calcula as médias com proteção contra divisão por zero
                peso_medio = sum(pesos) / len(pesos) if pesos else 0
                gmd_medio = sum(gmds) / len(gmds) if gmds else 0
                
                print(f"\nResultados do lote {lote.id_lote}:")
                print(f"- Número de animais com GMD calculado: {len(gmds)}")
                if gmds:
                    print(f"- GMDs individuais: {[round(gmd, 2) for gmd in gmds]}")
                else:
                    print("- Nenhum GMD calculado")
                print(f"- Peso médio: {peso_medio:.2f}kg")
                print(f"- GMD médio: {gmd_medio:.2f}kg/dia")
                
                # Adiciona os dados calculados ao lote
                lote.peso_medio = peso_medio
                lote.gmd_medio = gmd_medio
                
                lotes_data.append({
                    'lote': lote,
                    'quantidade_atual': quantidade_atual,
                    'peso_medio': peso_medio,
                    'gmd_medio': gmd_medio
                })
            except Exception as e:
                print(f"Erro ao processar lote {lote.id_lote}: {str(e)}")
                continue
        
        context['lotes'] = lotes_data
        return context

    def form_valid(self, form):
        try:
            form.instance.tipo = 'SN'
            form.instance.destino_lote_id = self.request.POST.get('lote')
            form.instance.consumo_pv = self.request.POST.get('consumo_pv')
            form.instance.usuario = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, 'Saída de nutrição registrada com sucesso!')
            return response
        except Exception as e:
            print(f"Erro ao salvar saída de nutrição: {str(e)}")
            messages.error(self.request, 'Erro ao registrar saída')
            return self.form_invalid(form)

class SaidaNutricaoView(ListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['insumos'] = Insumo.objects.all()
        
        # Busca os lotes e adiciona informações calculadas
        lotes = Lote.objects.all()
        lotes_data = []
        
        for lote in lotes:
            # Calcula a quantidade atual de animais
            quantidade_atual = Animal.objects.filter(lote=lote, situacao='ATIVO').count()
            
            # Calcula o peso médio e GMD do lote
            animais = Animal.objects.filter(lote=lote, situacao='ATIVO')
            pesos = []
            gmds = []
            
            for animal in animais:
                ultima_pesagem = Pesagem.objects.filter(
                    animal=animal
                ).order_by('-data').first()
                
                if ultima_pesagem:
                    pesos.append(ultima_pesagem.peso)
                    
                if hasattr(animal, 'gmd'):
                    gmds.append(animal.gmd)
            
            # Calcula as médias com proteção contra divisão por zero
            peso_medio = sum(pesos) / len(pesos) if pesos else 0
            gmd_medio = sum(gmds) / len(gmds) if gmds else 0
            
            # Adiciona os dados calculados ao lote
            lote.peso_medio = peso_medio
            lote.gmd_medio = gmd_medio
            lotes_data.append(lote)
            
        context['lotes'] = lotes_data
        return context

@login_required
def saida_nutricao_detail(request, pk):
    saida = get_object_or_404(MovimentacaoEstoque, pk=pk, tipo='SN', usuario=request.user)
    
    # Calcula estatísticas do lote na data da movimentação
    lote = saida.destino_lote
    if lote:
        # Busca animais que estavam no lote na data da movimentação
        animais = Animal.objects.filter(
            lote=lote,
            data_entrada__lte=saida.data
        ).exclude(
            data_saida__lt=saida.data  # Exclui apenas animais que saíram antes da data da movimentação
        ).select_related('categoria_animal', 'raca')
        
        peso_total = 0
        count = len(animais)
        animais_com_peso = []
        
        for animal in animais:
            ultima_pesagem = Pesagem.objects.filter(
                animal=animal,
                data__lte=saida.data
            ).order_by('-data').first()
            
            if ultima_pesagem:
                peso_total += ultima_pesagem.peso
                animais_com_peso.append({
                    'animal': animal,
                    'peso': ultima_pesagem.peso
                })
        
        peso_medio = peso_total / len(animais_com_peso) if animais_com_peso else 0
        count = len(animais_com_peso)  # Atualiza count para considerar apenas animais com peso
        
        # Calcula o consumo diário do lote
        consumo_diario_lote = peso_medio * count * (saida.consumo_pv / 100) if count > 0 and saida.consumo_pv else 0
        
        # Calcula o consumo por cabeça
        consumo_por_cabeca = saida.quantidade / count if count > 0 else 0
        
        # Calcula o valor por animal
        valor_por_animal = saida.valor_total / count if count > 0 else 0
        
        # Atualiza ou cria os rateios para cada animal
        RateioMovimentacao.objects.filter(movimentacao=saida).delete()  # Remove rateios antigos
        for animal_info in animais_com_peso:
            RateioMovimentacao.objects.create(
                movimentacao=saida,
                animal=animal_info['animal'],
                valor=valor_por_animal  # Usando o valor_por_animal correto
            )
    else:
        peso_medio = 0
        count = 0
        consumo_diario_lote = 0
        consumo_por_cabeca = 0
        valor_por_animal = 0
    
    # Busca os rateios atualizados
    rateios = RateioMovimentacao.objects.filter(
        movimentacao=saida
    ).select_related('animal', 'animal__categoria_animal', 'animal__raca')
    
    return render(request, 'estoque/saida_nutricao_detail.html', {
        'saida': saida,
        'rateios': rateios,
        'peso_medio': peso_medio,
        'quantidade_animais': count,
        'consumo_diario_lote': consumo_diario_lote,
        'consumo_por_cabeca': consumo_por_cabeca,
        'dias_duracao': saida.quantidade / consumo_diario_lote if consumo_diario_lote > 0 else 0
    })

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
    MovimentacaoEstoque.objects.create(
        insumo=insumo,
        tipo='E',
        data=despesa.data_emissao,
        quantidade=item_despesa.quantidade,
        valor_unitario=item_despesa.valor_unitario,
        despesa=despesa,
        usuario=despesa.usuario
    )

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
