from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, timedelta
import logging
import traceback

from .models import Animal, Lote, Fazenda
from .models_reproducao import EstacaoMonta, ManejoReproducao

logger = logging.getLogger(__name__)

@login_required
def estacao_monta_list(request):
    estacoes = EstacaoMonta.objects.filter(fazenda__usuario=request.user)
    return render(request, 'reproducao/estacao_monta_list.html', {'estacoes': estacoes})

@login_required
def estacao_monta_create(request):
    """Cria uma nova estação de monta."""
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            fazenda_id = request.POST.get('fazenda')
            data_inicio = request.POST.get('data_inicio')
            observacao = request.POST.get('observacoes')
            lotes_ids = request.POST.getlist('lotes')
            
            # Criar a estação de monta
            estacao = EstacaoMonta.objects.create(
                fazenda_id=fazenda_id,
                data_inicio=data_inicio,
                observacao=observacao
            )
            
            # Adicionar os lotes
            estacao.lotes.set(lotes_ids)
            
            messages.success(request, 'Estação de monta criada com sucesso!')
            return redirect('estacao_monta_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar estação de monta: {str(e)}')
            return redirect('estacao_monta_create')
    
    # GET: mostrar formulário
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'reproducao/estacao_monta_form.html', {
        'fazendas': fazendas
    })

@login_required
def estacao_monta_update(request, pk):
    estacao = get_object_or_404(EstacaoMonta, pk=pk, fazenda__usuario=request.user)
    
    if request.method == 'POST':
        try:
            fazenda = get_object_or_404(Fazenda, pk=request.POST.get('fazenda'), usuario=request.user)
            estacao.data_inicio = request.POST.get('data_inicio')
            estacao.fazenda = fazenda
            estacao.observacoes = request.POST.get('observacoes')
            estacao.save()
            estacao.lotes.set(request.POST.getlist('lotes'))
            messages.success(request, 'Estação de Monta atualizada com sucesso!')
            return redirect('estacao_monta_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar Estação de Monta: {str(e)}')
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    lotes = Lote.objects.filter(fazenda=estacao.fazenda)
    return render(request, 'reproducao/estacao_monta_form.html', {
        'object': estacao,
        'fazendas': fazendas,
        'lotes': lotes
    })

@login_required
def estacao_monta_delete(request, pk):
    estacao = get_object_or_404(EstacaoMonta, pk=pk, fazenda__usuario=request.user)
    if request.method == 'POST':
        estacao.delete()
        messages.success(request, 'Estação de Monta excluída com sucesso!')
        return redirect('estacao_monta_list')
    return render(request, 'reproducao/estacao_monta_confirm_delete.html', {'estacao': estacao})

@login_required
def concepcao_form(request):
    estacoes = EstacaoMonta.objects.filter(fazenda__usuario=request.user)
    return render(request, 'reproducao/concepcao_form.html', {'estacoes': estacoes})

@login_required
def diagnostico_form(request):
    estacoes = EstacaoMonta.objects.filter(fazenda__usuario=request.user)
    return render(request, 'reproducao/diagnostico_form.html', {'estacoes': estacoes})

@login_required
def resultado_form(request):
    estacoes = EstacaoMonta.objects.filter(fazenda__usuario=request.user)
    return render(request, 'reproducao/resultado_form.html', {'estacoes': estacoes})

@login_required
def diagnostico_list(request):
    """Lista todos os manejos reprodutivos."""
    manejos = ManejoReproducao.objects.filter(
        estacao_monta__fazenda__usuario=request.user
    ).order_by('-data_diagnostico', '-data_concepcao', '-data_resultado')
    
    return render(request, 'reproducao/diagnostico_list.html', {
        'manejos': manejos
    })

@login_required
def get_lotes_estacao(request):
    estacao_id = request.GET.get('estacao_id')
    if estacao_id:
        estacao = get_object_or_404(EstacaoMonta, pk=estacao_id)
        lotes = estacao.lotes.all()
        return JsonResponse({
            'lotes': [{'id': lote.id, 'nome': str(lote)} for lote in lotes]
        })
    return JsonResponse({'lotes': []})

@login_required
def get_lotes_por_fazenda(request, fazenda_id):
    """Retorna os lotes de uma fazenda em formato JSON."""
    try:
        fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)
        
        lotes = Lote.objects.filter(fazenda=fazenda)
        
        data = []
        for lote in lotes:
            qtd_animais = lote.animal_set.filter(situacao='ATIVO').count()
            data.append({
                'id': lote.id,
                'id_lote': lote.id_lote,
                'nome': lote.id_lote,  
                'quantidade_animais': qtd_animais,
                'text': f'{lote.id_lote} ({qtd_animais} animais)'
            })
        
        return JsonResponse({'lotes': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def buscar_animal(request):
    """Busca um animal pelo brinco."""
    try:
        brinco = request.GET.get('brinco')
        lote_id = request.GET.get('lote_id')
        estacao_id = request.GET.get('estacao_id')
        
        logger.info(f"Buscando animal - Brinco: {brinco}, Lote: {lote_id}, Estação: {estacao_id}")
        
        if not brinco or not lote_id:
            return JsonResponse({
                'success': False,
                'error': 'Informe o brinco e o lote do animal'
            }, status=400)
        
        # Busca o animal pelo brinco visual ou eletrônico
        try:
            animal = Animal.objects.get(
                Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco),
                lote_id=lote_id,
                lote__fazenda__usuario=request.user,
                situacao='ATIVO'
            )
            
            logger.info(f"Animal encontrado: {animal.id}")
            
            # Verifica se já existe manejo para este animal na estação
            manejo_existente = None
            if estacao_id:
                manejo_existente = ManejoReproducao.objects.filter(
                    animal=animal,
                    estacao_monta_id=estacao_id
                ).first()
                
                if manejo_existente:
                    logger.info(f"Manejo encontrado: {manejo_existente.id}")
            
            # Prepara os dados de retorno
            data = {
                'success': True,
                'animal': {
                    'id': animal.id,
                    'brinco_visual': animal.brinco_visual,
                    'brinco_eletronico': animal.brinco_eletronico,
                    'categoria': str(animal.categoria_animal),
                    'data_nascimento': animal.data_nascimento.strftime('%d/%m/%Y') if animal.data_nascimento else None,
                }
            }
            
            # Se existir manejo, adiciona os dados
            if manejo_existente:
                data['manejo_existente'] = {
                    'id': manejo_existente.id,
                    'data_concepcao': manejo_existente.data_concepcao.strftime('%d/%m/%Y') if manejo_existente.data_concepcao else None,
                    'previsao_parto': manejo_existente.previsao_parto.strftime('%d/%m/%Y') if manejo_existente.previsao_parto else None,
                    'data_diagnostico': manejo_existente.data_diagnostico.strftime('%d/%m/%Y') if manejo_existente.data_diagnostico else None,
                    'data_resultado': manejo_existente.data_resultado.strftime('%d/%m/%Y') if manejo_existente.data_resultado else None,
                    'diagnostico': manejo_existente.diagnostico,
                    'resultado': manejo_existente.resultado
                }
            
            return JsonResponse(data)
            
        except Animal.DoesNotExist:
            logger.warning(f"Animal não encontrado - Brinco: {brinco}, Lote: {lote_id}")
            return JsonResponse({
                'success': False,
                'error': 'Animal não encontrado neste lote'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Erro ao buscar animal: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar animal: {str(e)}'
        }, status=500)

@login_required
def salvar_manejo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        data = request.POST
        animal_id = data.get('animal_id')
        estacao_id = data.get('estacao_monta')
        lote_id = data.get('lote')
        
        # Log dos dados recebidos
        logger.info(f"Dados recebidos no salvar_manejo:")
        logger.info(f"animal_id: {animal_id}")
        logger.info(f"estacao_id: {estacao_id}")
        logger.info(f"lote_id: {lote_id}")
        logger.info(f"tipo_manejo: {data.get('tipo_manejo')}")
        logger.info(f"diagnostico: {data.get('diagnostico')}")
        logger.info(f"data_diagnostico: {data.get('data_diagnostico')}")
        
        if not all([animal_id, estacao_id, lote_id]):
            logger.warning("Dados incompletos no salvar_manejo")
            logger.warning(f"POST data: {dict(data)}")
            return JsonResponse({
                'success': False,
                'error': 'Dados incompletos. Verifique se selecionou o animal, estação e lote.'
            }, status=400)
        
        manejo = ManejoReproducao.objects.filter(
            animal_id=animal_id,
            estacao_monta_id=estacao_id
        ).first()
        
        if not manejo:
            manejo = ManejoReproducao(
                animal_id=animal_id,
                estacao_monta_id=estacao_id,
                lote_id=lote_id
            )
        
        tipo_manejo = data.get('tipo_manejo')
        
        if tipo_manejo == 'concepcao':
            data_concepcao = data.get('data_concepcao')
            if data_concepcao:
                manejo.data_concepcao = datetime.strptime(data_concepcao, '%Y-%m-%d').date()
        elif tipo_manejo == 'diagnostico':
            data_diagnostico = data.get('data_diagnostico')
            if data_diagnostico:
                manejo.data_diagnostico = datetime.strptime(data_diagnostico, '%Y-%m-%d').date()
            manejo.diagnostico = data.get('diagnostico')
        elif tipo_manejo == 'resultado':
            data_resultado = data.get('data_resultado')
            if data_resultado:
                manejo.data_resultado = datetime.strptime(data_resultado, '%Y-%m-%d').date()
            manejo.resultado = data.get('resultado')
            
        manejo.save()
        
        if data.get('fazer_movimentacao') == 'true':
            novo_lote_id = data.get('novo_lote')
            if novo_lote_id:
                animal = manejo.animal
                animal.lote_id = novo_lote_id
                animal.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Manejo salvo com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar manejo: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error(f"POST data: {dict(data)}")
        
        # Trata o erro de forma mais amigável
        error_msg = str(e)
        if isinstance(e, ValueError):
            error_msg = "Dados inválidos. Verifique se preencheu todos os campos corretamente."
        
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=400)
