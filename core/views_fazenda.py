from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Fazenda, Pasto, Benfeitoria
import json

@login_required
def get_all_pastos(request):
    """Retorna todos os pastos de todas as fazendas"""
    try:
        pastos = Pasto.objects.all()
        pastos_data = []
        for pasto in pastos:
            if pasto.coordenadas:
                pastos_data.append({
                    'id': pasto.id,
                    'nome': pasto.nome,
                    'area': pasto.area,
                    'coordenadas': pasto.coordenadas,
                    'fazenda': pasto.fazenda.nome
                })
        return JsonResponse({'success': True, 'pastos': pastos_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_all_benfeitorias(request):
    """Retorna todas as benfeitorias de todas as fazendas"""
    try:
        benfeitorias = Benfeitoria.objects.all()
        benfeitorias_data = []
        for b in benfeitorias:
            if b.coordenadas:
                benfeitorias_data.append({
                    'id': b.id,
                    'nome': b.nome,
                    'valor_compra': str(b.valor_compra),
                    'data_aquisicao': b.data_aquisicao.strftime('%d/%m/%Y') if b.data_aquisicao else None,
                    'coordenadas': b.coordenadas,
                    'fazenda': b.fazenda.nome
                })
        return JsonResponse({'success': True, 'benfeitorias': benfeitorias_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_pastos_fazenda(request, fazenda_id):
    """Retorna os pastos de uma fazenda específica"""
    try:
        fazenda = get_object_or_404(Fazenda, id=fazenda_id)
        pastos = Pasto.objects.filter(fazenda=fazenda)
        pastos_data = []
        for pasto in pastos:
            if pasto.coordenadas:
                pastos_data.append({
                    'id': pasto.id,
                    'nome': pasto.nome,
                    'area': pasto.area,
                    'coordenadas': pasto.coordenadas
                })
        return JsonResponse({'success': True, 'pastos': pastos_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_cidade_fazenda(request, fazenda_id):
    """Retorna a cidade de uma fazenda específica"""
    try:
        fazenda = get_object_or_404(Fazenda, id=fazenda_id)
        return JsonResponse({'success': True, 'cidade': fazenda.cidade})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_benfeitorias_fazenda(request, fazenda_id):
    """Retorna as benfeitorias de uma fazenda específica"""
    try:
        fazenda = get_object_or_404(Fazenda, id=fazenda_id)
        benfeitorias = Benfeitoria.objects.filter(fazenda=fazenda)
        benfeitorias_data = []
        for b in benfeitorias:
            if b.coordenadas:
                benfeitorias_data.append({
                    'id': b.id,
                    'nome': b.nome,
                    'valor_compra': str(b.valor_compra),
                    'data_aquisicao': b.data_aquisicao.strftime('%d/%m/%Y') if b.data_aquisicao else None,
                    'coordenadas': b.coordenadas
                })
        return JsonResponse({'success': True, 'benfeitorias': benfeitorias_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def salvar_coordenadas_benfeitoria(request):
    """Salva as coordenadas de uma benfeitoria"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            benfeitoria_id = data.get('benfeitoria_id')
            coordenadas = data.get('coordenadas')
            
            benfeitoria = get_object_or_404(Benfeitoria, id=benfeitoria_id)
            benfeitoria.coordenadas = coordenadas
            benfeitoria.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def get_coordenadas_benfeitoria(request, benfeitoria_id):
    """Retorna as coordenadas de uma benfeitoria específica"""
    try:
        benfeitoria = get_object_or_404(Benfeitoria, id=benfeitoria_id)
        return JsonResponse({
            'success': True,
            'coordenadas': benfeitoria.coordenadas
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
