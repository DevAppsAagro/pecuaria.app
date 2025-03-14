from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from ..models import Animal, Pesagem, ManejoSanitario, Lote, Pasto, MovimentacaoAnimal

@login_required
def buscar_animal(request, brinco):
    """
    Busca um animal pelo brinco visual ou eletrônico e retorna suas informações.
    Inclui os dados do animal, última pesagem e dados de entrada.
    """
    try:
        # Buscar o animal pelo brinco visual ou eletrônico
        animal = Animal.objects.filter(Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco)).first()
        
        if not animal:
            return JsonResponse({
                'success': False,
                'message': f'Animal com brinco {brinco} não encontrado'
            })
            
        # Buscar a última pesagem do animal
        ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
        
        # Montar os dados do animal
        animal_data = {
            'id': animal.id,
            'brinco': animal.brinco_visual or animal.brinco_eletronico,
            'raca': animal.raca.nome if animal.raca else 'N/A',
            'categoria': animal.categoria_animal.nome if animal.categoria_animal else 'N/A',
            'lote': str(animal.lote) if animal.lote else 'N/A',
            'pasto': animal.pasto_atual.nome if animal.pasto_atual else 'N/A',
            'lote_id': animal.lote.id if animal.lote else None,
            'pasto_id': animal.pasto_atual.id if animal.pasto_atual else None,
            'fazenda_id': animal.fazenda_atual.id if animal.fazenda_atual else None,
            'peso_entrada': animal.peso_entrada,
            'data_entrada': animal.data_entrada.strftime('%Y-%m-%d') if animal.data_entrada else None
        }
        
        # Dados da última pesagem
        ultima_pesagem_data = None
        gmd = None
        
        if ultima_pesagem:
            ultima_pesagem_data = {
                'id': ultima_pesagem.id,
                'peso': ultima_pesagem.peso,
                'data': ultima_pesagem.data.strftime('%Y-%m-%d')
            }
            
            # Buscar a pesagem anterior para calcular o GMD histórico
            pesagem_anterior = Pesagem.objects.filter(
                animal=animal, 
                data__lt=ultima_pesagem.data
            ).order_by('-data').first()
            
            # Se não houver pesagem anterior, usar o peso de entrada como referência
            if not pesagem_anterior and animal.peso_entrada and animal.data_entrada:
                # Calcular a diferença entre a última pesagem e o peso de entrada
                diff_peso = ultima_pesagem.peso - animal.peso_entrada
                diff_dias = (ultima_pesagem.data - animal.data_entrada).days
                
                print(f"DEBUG GMD: Usando peso de entrada: {animal.peso_entrada}, data: {animal.data_entrada}")
                print(f"DEBUG GMD: Última pesagem: {ultima_pesagem.peso}, data: {ultima_pesagem.data}")
                print(f"DEBUG GMD: diff_peso = {diff_peso}, diff_dias = {diff_dias}")
                
                if diff_dias > 0:
                    gmd = round(diff_peso / diff_dias, 3)
                    print(f"DEBUG GMD: calculado com peso de entrada = {gmd}")
            elif pesagem_anterior:
                # Calcular a diferença de peso e dias
                diff_peso = ultima_pesagem.peso - pesagem_anterior.peso
                diff_dias = (ultima_pesagem.data - pesagem_anterior.data).days
                
                print(f"DEBUG GMD: peso atual = {ultima_pesagem.peso}, peso anterior = {pesagem_anterior.peso}")
                print(f"DEBUG GMD: data atual = {ultima_pesagem.data}, data anterior = {pesagem_anterior.data}")
                print(f"DEBUG GMD: diff_peso = {diff_peso}, diff_dias = {diff_dias}")
                
                if diff_dias > 0:
                    gmd = round(diff_peso / diff_dias, 3)
                    print(f"DEBUG GMD: calculado = {gmd}")
                else:
                    print("DEBUG GMD: diff_dias <= 0, impossível calcular GMD")
            else:
                print("DEBUG GMD: não há dados para calcular GMD")
        
        print(f"DEBUG: Animal: {animal_data}, Ultima pesagem: {ultima_pesagem_data}, GMD: {gmd}")
        
        # Retornar os dados como JSON
        return JsonResponse({
            'success': True,
            'animal': animal_data,
            'ultima_pesagem': ultima_pesagem_data,
            'gmd': gmd
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': str(e)})

@require_http_methods(['POST'])
def registrar_manejo(request):
    """
    Registra um novo manejo para um animal.
    - Pesagem: Registra um novo peso para o animal.
    - Manejo Sanitário: Registra um novo manejo sanitário para o animal.
    - Apartação: Move o animal para um novo lote/pasto com base no peso.
    """
    try:
        data = request.POST
        brinco = data.get('brinco')
        peso = data.get('peso')
        data_manejo = data.get('data')
        fazer_manejo = data.get('fazer_manejo') == 'on'
        fazer_apartacao = data.get('fazer_apartacao') == 'on'
        
        # Buscar animal pelo brinco visual ou eletrônico
        try:
            animal = Animal.objects.filter(Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco)).first()
            if not animal:
                return JsonResponse({
                    'success': False,
                    'message': f'Animal com brinco {brinco} não encontrado'
                })
        except Exception as e:
            print(f"Erro ao buscar animal: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro ao buscar animal: {str(e)}'
            })
        
        # Registrar pesagem
        if peso:
            try:
                pesagem = Pesagem(
                    animal=animal,
                    peso=float(peso),
                    data=data_manejo,
                    usuario=request.user if hasattr(request, 'user') else None
                )
                pesagem.save()
                print(f"Pesagem registrada para o animal {brinco}: {peso}kg em {data_manejo}")
            except Exception as e:
                print(f"Erro ao registrar pesagem: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao registrar pesagem: {str(e)}'
                })
        
        # Registrar manejo sanitário
        if fazer_manejo:
            try:
                insumo = data.get('insumo', '')
                tipo_manejo = data.get('tipo_manejo', '')
                dias_proximo = data.get('dias_proximo', '0')  # Usando '0' como valor padrão
                observacao = data.get('observacao', '')
                
                manejo = ManejoSanitario(
                    animal=animal,
                    data=data_manejo,
                    insumo=insumo,
                    tipo_manejo=tipo_manejo,
                    dias_proximo_manejo=int(dias_proximo) if dias_proximo else 0,  # Convertendo para int com valor padrão 0
                    observacao=observacao,
                    usuario=request.user if hasattr(request, 'user') else None
                )
                manejo.save()
                print(f"Manejo sanitário registrado para o animal {brinco}")
            except Exception as e:
                print(f"Erro ao registrar manejo sanitário: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao registrar manejo sanitário: {str(e)}'
                })
        
        # Realizar apartação
        if fazer_apartacao and peso:
            try:
                peso_referencia = float(data.get('peso_referencia', 0))
                peso_float = float(peso)
                
                if peso_float > peso_referencia:
                    # Animal acima do peso de referência
                    lote_id = data.get('lote_acima')
                    pasto_id = data.get('pasto_acima')
                else:
                    # Animal abaixo do peso de referência
                    lote_id = data.get('lote_abaixo')
                    pasto_id = data.get('pasto_abaixo')
                
                lote_anterior = animal.lote
                pasto_anterior = animal.pasto_atual
                
                # Movimentação de lote
                if lote_id and lote_id.strip():
                    try:
                        lote = Lote.objects.get(id=lote_id)
                        
                        # Criar movimentação de lote
                        MovimentacaoAnimal.objects.create(
                            animal=animal,
                            data_movimentacao=data_manejo,
                            tipo='LOTE',
                            lote_origem=lote_anterior,
                            lote_destino=lote,
                            motivo=f"Apartação por peso: {peso}kg",
                            usuario=request.user if hasattr(request, 'user') else None
                        )
                        
                        # Atualizar o lote do animal
                        animal.lote = lote
                        animal.save()
                        print(f"Animal {brinco} movido para o lote {str(lote)}")
                    except Lote.DoesNotExist:
                        print(f"Lote com ID {lote_id} não encontrado")
                
                # Movimentação de pasto
                if pasto_id and pasto_id.strip():
                    try:
                        pasto = Pasto.objects.get(id=pasto_id)
                        
                        # Criar movimentação de pasto
                        MovimentacaoAnimal.objects.create(
                            animal=animal,
                            data_movimentacao=data_manejo,
                            tipo='PASTO',
                            pasto_origem=pasto_anterior,
                            pasto_destino=pasto,
                            motivo=f"Apartação por peso: {peso}kg",
                            usuario=request.user if hasattr(request, 'user') else None
                        )
                        
                        # Atualizar o pasto do animal
                        animal.pasto_atual = pasto
                        animal.save()
                        print(f"Animal {brinco} movido para o pasto {pasto.nome}")
                    except Pasto.DoesNotExist:
                        print(f"Pasto com ID {pasto_id} não encontrado")
            except Exception as e:
                print(f"Erro ao realizar apartação: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao realizar apartação: {str(e)}'
                })
        
        return JsonResponse({
            'success': True,
            'message': 'Manejo registrado com sucesso'
        })
    except Exception as e:
        print(f"Erro ao registrar manejo: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao registrar manejo: {str(e)}'
        })

@require_http_methods(['GET'])
def lotes_por_fazenda(request, fazenda_id):
    """
    Retorna todos os lotes de uma fazenda específica.
    """
    try:
        lotes = Lote.objects.filter(fazenda_id=fazenda_id)
        
        if not lotes.exists():
            return JsonResponse({
                'success': False,
                'message': 'Nenhum lote encontrado para esta fazenda'
            })
        
        lotes_data = []
        for lote in lotes:
            lotes_data.append({
                'id': lote.id,
                'nome': str(lote)  # Usando a representação de string do lote (id_lote - finalidade)
            })
        
        return JsonResponse({
            'success': True,
            'lotes': lotes_data
        })
    except Exception as e:
        print(f"Erro ao buscar lotes: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro ao buscar lotes da fazenda'
        })

@require_http_methods(['GET'])
def pastos_por_fazenda(request, fazenda_id):
    """
    Retorna todos os pastos de uma fazenda específica.
    """
    try:
        pastos = Pasto.objects.filter(fazenda_id=fazenda_id)
        
        if not pastos.exists():
            return JsonResponse({
                'success': False,
                'message': 'Nenhum pasto encontrado para esta fazenda'
            })
        
        pastos_data = []
        for pasto in pastos:
            # Usar o nome se disponível, caso contrário usar a representação de string
            nome_pasto = pasto.nome if pasto.nome else str(pasto)
            pastos_data.append({
                'id': pasto.id,
                'nome': nome_pasto
            })
        
        return JsonResponse({
            'success': True,
            'pastos': pastos_data
        })
    except Exception as e:
        print(f"Erro ao buscar pastos: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro ao buscar pastos da fazenda'
        })
