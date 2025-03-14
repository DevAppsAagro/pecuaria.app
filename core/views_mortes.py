from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import HttpResponse
from openpyxl import Workbook
from django.db.models import Q, Sum
from decimal import Decimal
import json

from .models import Animal, MotivoMorte, RegistroMorte, RateioCusto
from .models_compras import CompraAnimal

# Registro de Mortes - Views baseadas em função
@login_required
def morte_list(request):
    """Lista todos os registros de morte de animais do usuário."""
    registros = RegistroMorte.objects.filter(usuario=request.user)
    
    # Filtragem
    motivo = request.GET.get('motivo')
    if motivo:
        registros = registros.filter(motivo_id=motivo)
    
    data_inicio = request.GET.get('data_inicio')
    if data_inicio:
        registros = registros.filter(data_morte__gte=data_inicio)
        
    data_fim = request.GET.get('data_fim')
    if data_fim:
        registros = registros.filter(data_morte__lte=data_fim)
    
    # Paginação
    paginator = Paginator(registros, 10)
    page = request.GET.get('page')
    registros_paginados = paginator.get_page(page)
    
    # Obtém os motivos de morte para o filtro
    motivos = MotivoMorte.objects.filter(usuario=request.user)
    
    context = {
        'registros': registros_paginados,
        'motivos': motivos,
        'active_tab': 'animais'
    }
    
    return render(request, 'animais/morte_list.html', context)

@login_required
def morte_create(request):
    """Cria um novo registro de morte de animal."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                animal_id = request.POST.get('animal')
                animal = get_object_or_404(Animal, id=animal_id, usuario=request.user)
                
                # Verifica se o animal já está registrado como morto
                if animal.situacao == 'MORTO':
                    messages.error(request, f'O animal {animal.brinco_visual} já está registrado como morto.')
                    return redirect('morte_create')
                
                motivo_id = request.POST.get('motivo')
                motivo = get_object_or_404(MotivoMorte, id=motivo_id, usuario=request.user)
                
                data_morte = request.POST.get('data_morte')
                observacao = request.POST.get('observacao', '')
                
                # Se o prejuízo foi informado, converte para Decimal
                prejuizo_str = request.POST.get('prejuizo', '')
                prejuizo = None
                if prejuizo_str.strip():
                    prejuizo = Decimal(prejuizo_str.replace('.', '').replace(',', '.'))
                
                # Cria o registro de morte
                RegistroMorte.objects.create(
                    animal=animal,
                    motivo=motivo,
                    data_morte=data_morte,
                    observacao=observacao,
                    prejuizo=prejuizo if prejuizo is not None else Decimal('0.00'),
                    usuario=request.user
                )
                
                messages.success(request, f'Morte do animal {animal.brinco_visual} registrada com sucesso.')
                return redirect('morte_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao registrar morte: {str(e)}')
            return redirect('morte_create')
            
    # GET - Exibe o formulário
    motivos = MotivoMorte.objects.filter(usuario=request.user)
    context = {
        'motivos': motivos,
        'active_tab': 'animais'
    }
    return render(request, 'animais/morte_form.html', context)

@login_required
def morte_update(request, pk):
    """Atualiza um registro de morte existente."""
    registro = get_object_or_404(RegistroMorte, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                motivo_id = request.POST.get('motivo')
                motivo = get_object_or_404(MotivoMorte, id=motivo_id, usuario=request.user)
                
                data_morte = request.POST.get('data_morte')
                observacao = request.POST.get('observacao', '')
                
                # Se o prejuízo foi informado, converte para Decimal
                prejuizo_str = request.POST.get('prejuizo', '')
                if prejuizo_str.strip():
                    prejuizo = Decimal(prejuizo_str.replace('.', '').replace(',', '.'))
                    registro.prejuizo = prejuizo
                
                registro.motivo = motivo
                registro.data_morte = data_morte
                registro.observacao = observacao
                registro.save()
                
                # Atualiza também a data de saída do animal
                animal = registro.animal
                animal.data_saida = data_morte
                animal.save(update_fields=['data_saida'])
                
                messages.success(request, f'Registro de morte atualizado com sucesso.')
                return redirect('morte_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao atualizar registro: {str(e)}')
    
    # GET - Exibe o formulário com os dados atuais
    motivos = MotivoMorte.objects.filter(usuario=request.user)
    context = {
        'registro': registro,
        'motivos': motivos,
        'active_tab': 'animais'
    }
    return render(request, 'animais/morte_form.html', context)

@login_required
def morte_delete(request, pk):
    """Exclui um registro de morte."""
    registro = get_object_or_404(RegistroMorte, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                animal = registro.animal
                registro.delete()
                
                # Verifica se há outros registros de morte para este animal
                if not RegistroMorte.objects.filter(animal=animal).exists():
                    # Restaura a situação do animal para ativo apenas se não houver outros registros
                    animal.situacao = 'ATIVO'
                    animal.data_saida = None
                    animal.save(update_fields=['situacao', 'data_saida'])
                
                messages.success(request, 'Registro de morte excluído com sucesso.')
                return redirect('morte_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir registro: {str(e)}')
    
    context = {
        'registro': registro,
        'active_tab': 'animais'
    }
    return render(request, 'animais/morte_confirm_delete.html', context)

@login_required
def buscar_animal_ajax(request):
    """Função AJAX para buscar animal pelo brinco."""
    termo = request.GET.get('termo', '')
    
    if not termo:
        return JsonResponse({"results": []})
    
    # Busca por brinco visual ou eletrônico
    animais = Animal.objects.filter(
        Q(brinco_visual__icontains=termo) | Q(brinco_eletronico__icontains=termo),
        usuario=request.user,
        situacao='ATIVO'
    )[:10]
    
    results = []
    for animal in animais:
        # Calcula o custo total do animal
        custo_total = RateioCusto.objects.filter(animal=animal).aggregate(Sum('valor'))['valor__sum'] or 0
        
        # Valor de compra (de compras anteriores)
        valor_compra = 0
        compra_animal = CompraAnimal.objects.filter(animal=animal).first()
        if compra_animal and compra_animal.valor_total:
            valor_compra = float(compra_animal.valor_total)
        
        results.append({
            "id": animal.id,
            "text": f"{animal.brinco_visual} - {animal.raca.nome}",
            "brinco_visual": animal.brinco_visual,
            "brinco_eletronico": animal.brinco_eletronico or "-",
            "raca": animal.raca.nome,
            "fazenda": animal.fazenda_atual.nome,
            "custo_total": float(custo_total),
            "valor_compra": valor_compra
        })
    
    return JsonResponse({"results": results})
