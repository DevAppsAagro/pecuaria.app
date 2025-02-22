from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Q, Count, Sum, Max, F, Value, DecimalField, ExpressionWrapper, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime import datetime, date, timedelta
from .auth_supabase import update_password
import json
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from django.urls import reverse

from .models import (
    Fazenda, Pasto, Animal, Lote, MovimentacaoAnimal, 
    VariedadeCapim, Raca, FinalidadeLote, CategoriaAnimal,
    UnidadeMedida, MotivoMorte, CategoriaCusto, SubcategoriaCusto,
    Pesagem, ManejoSanitario, Maquina, Benfeitoria, ContaBancaria, 
    Contato, Despesa, ItemDespesa, ParcelaDespesa, RateioCusto, ExtratoBancario
)

from .models_estoque import Insumo, MovimentacaoEstoque
from .models_compras import Compra, CompraAnimal
from .models_vendas import Venda, VendaAnimal
from .models_abates import Abate, AbateAnimal

from .forms import *
from .views_estatisticas import get_estatisticas_animais, get_estatisticas_detalhadas
from .auth_supabase import register_with_email, login_with_email, reset_password, verify_email

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if login_with_email(request, email, password):
            return redirect('dashboard')
            
    return render(request, 'registration/login.html')

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if register_with_email(request, email, password, first_name, last_name):
            messages.success(request, 'Conta criada com sucesso! Por favor, verifique seu email.')
            return redirect('login')
            
    return render(request, 'registration/register.html')

def reset_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if reset_password(email):
            messages.success(request, 'Um email foi enviado com instruções para redefinir sua senha.')
            return redirect('login')
        else:
            messages.error(request, 'Erro ao enviar email de redefinição de senha.')
    
    return render(request, 'registration/reset_password.html')

def verificar_email_view(request):
    return render(request, 'registration/verificar_email.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('login')

@login_required
def dashboard_view(request):
    return render(request, 'em_desenvolvimento.html', {'titulo': 'Dashboard'})

@login_required
def em_desenvolvimento(request):
    titulo = request.path.strip('/').replace('/', ' ').title()
    if 'configuracoes' in request.path:
        return render(request, 'configuracoes/configuracoes.html')
    return render(request, 'em_desenvolvimento.html', {'titulo': titulo})

@login_required
def fazenda_list(request):
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'fazendas/fazenda_list.html', {'fazendas': fazendas})

@login_required
def fazenda_create(request):
    ESTADOS_BRASIL = [
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'),
        ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'),
        ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
        ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'),
        ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),
        ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'),
        ('TO', 'Tocantins')
    ]
    
    if request.method == 'POST':
        data = {
            'nome': request.POST.get('nome'),
            'arrendada': request.POST.get('arrendada') == 'on',
            'inscricao_estadual': request.POST.get('inscricao_estadual'),
            'cidade': request.POST.get('cidade'),
            'estado': request.POST.get('estado'),
            'area_total': Decimal(request.POST.get('area_total').replace(',', '.')),
            'usuario': request.user
        }
        
        if not data['arrendada']:
            data['valor_hectare'] = Decimal(request.POST.get('valor_hectare', '0').replace(',', '.'))
            data['custo_oportunidade'] = Decimal(request.POST.get('custo_oportunidade', '0').replace(',', '.'))
        
        fazenda = Fazenda.objects.create(**data)
        messages.success(request, 'Fazenda cadastrada com sucesso!')
        return redirect('fazenda_list')
    
    return render(request, 'fazendas/fazenda_form.html', {
        'titulo': 'Nova Fazenda',
        'estados': ESTADOS_BRASIL
    })

@login_required
def fazenda_edit(request, pk):
    fazenda = get_object_or_404(Fazenda, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        fazenda.nome = request.POST.get('nome')
        fazenda.arrendada = request.POST.get('arrendada') == 'on'
        fazenda.inscricao_estadual = request.POST.get('inscricao_estadual')
        fazenda.cidade = request.POST.get('cidade')
        fazenda.estado = request.POST.get('estado')
        fazenda.area_total = Decimal(request.POST.get('area_total').replace(',', '.'))
        
        if not fazenda.arrendada:
            fazenda.valor_hectare = Decimal(request.POST.get('valor_hectare', '0').replace(',', '.'))
            fazenda.custo_oportunidade = Decimal(request.POST.get('custo_oportunidade', '0').replace(',', '.'))
        else:
            fazenda.valor_hectare = None
            fazenda.custo_oportunidade = None
        
        fazenda.save()
        messages.success(request, 'Fazenda atualizada com sucesso!')
        return redirect('fazenda_list')
    
    return render(request, 'fazendas/fazenda_form.html', {
        'fazenda': fazenda,
        'titulo': 'Editar Fazenda',
        'estados': Fazenda.ESTADOS_CHOICES
    })

@login_required
def fazenda_delete(request, pk):
    fazenda = get_object_or_404(Fazenda, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        fazenda.delete()
        messages.success(request, 'Fazenda excluída com sucesso!')
        return redirect('fazenda_list')
    
    return render(request, 'fazendas/fazenda_delete.html', {'fazenda': fazenda})

@login_required
def fazendas_view(request):
    return render(request, 'em_desenvolvimento.html')

@login_required
def animais_view(request):
    return render(request, 'em_desenvolvimento.html')

@login_required
def manejos_view(request):
    # Buscar últimos registros
    pesagens = Pesagem.objects.filter(usuario=request.user).order_by('-data')[:20]
    manejos = ManejoSanitario.objects.filter(usuario=request.user).order_by('-data')[:20]
    
    context = {
        'pesagens': pesagens,
        'manejos': manejos,
        'active_tab': 'manejos'
    }
    
    return render(request, 'manejos/manejo_list.html', context)

@login_required
def manejo_create(request):
    if request.method == 'POST':
        try:
            animal_brinco = request.POST.get('brinco')
            animal = Animal.objects.get(Q(brinco_visual=animal_brinco) | Q(brinco_eletronico=animal_brinco))
            
            # Registrar pesagem
            peso = request.POST.get('peso')
            if peso:
                Pesagem.objects.create(
                    animal=animal,
                    data=request.POST.get('data'),
                    peso=peso,
                    usuario=request.user
                )
            
            # Registrar manejo sanitário se checkbox marcado
            if request.POST.get('fazer_manejo') == 'on':
                ManejoSanitario.objects.create(
                    animal=animal,
                    data=request.POST.get('data'),
                    insumo=request.POST.get('insumo'),
                    tipo_manejo=request.POST.get('tipo_manejo'),
                    dias_proximo_manejo=request.POST.get('dias_proximo'),
                    observacao=request.POST.get('observacao'),
                    usuario=request.user
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Manejo registrado com sucesso!'
            })
            
        except Animal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Animal não encontrado!'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    context = {
        'active_tab': 'manejos'
    }
    return render(request, 'manejos/manejo_form.html', context)

@login_required
def buscar_animal(request, brinco):
    try:
        animal = Animal.objects.get(Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco), usuario=request.user)
        ultima_pesagem = Pesagem.objects.filter(animal=animal).order_by('-data').first()
        
        data = {
            'success': True,
            'animal': {
                'id': animal.id,
                'brinco_visual': animal.brinco_visual,
                'categoria': str(animal.categoria_animal),
                'lote': animal.lote.id_lote
            }
        }
        
        if ultima_pesagem:
            # Se tem pesagem, usa ela
            data['ultima_pesagem'] = {
                'peso': float(ultima_pesagem.peso),
                'data': ultima_pesagem.data.strftime('%Y-%m-%d')
            }
        elif animal.peso_entrada:
            # Se não tem pesagem mas tem peso de entrada, usa ele
            data['ultima_pesagem'] = {
                'peso': float(animal.peso_entrada),
                'data': animal.data_entrada.strftime('%Y-%m-%d')
            }
        
        return JsonResponse(data)
    except Animal.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Animal não encontrado'})
    except Exception as e:
        messages.error(request, f"Erro ao buscar animal: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def financeiro_view(request):
    return render(request, 'em_desenvolvimento.html')

def awaiting_payment(request):
    return render(request, 'registration/awaiting_payment.html')

@login_required
def pasto_list(request):
    try:
        # Filtro de fazenda
        fazenda_id = request.GET.get('fazenda')
        
        # Buscar todas as fazendas para o select
        fazendas = Fazenda.objects.filter(usuario=request.user)
        
        # Filtrar pastos
        if fazenda_id:
            pastos = Pasto.objects.filter(fazenda_id=fazenda_id, fazenda__usuario=request.user)
        else:
            pastos = Pasto.objects.filter(fazenda__usuario=request.user)
        
        # Preparar dados dos pastos para o mapa
        pastos_json = []
        cores_fazendas = {}
        
        # Cores pré-definidas para as fazendas
        cores = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', 
                '#800000', '#008000', '#000080', '#808000', '#800080', '#008080']
        
        for idx, fazenda in enumerate(fazendas):
            cores_fazendas[fazenda.id] = cores[idx % len(cores)]
        
        for pasto in pastos:
            pastos_json.append({
                'id': pasto.id,
                'id_pasto': pasto.id_pasto,
                'nome': pasto.nome,
                'fazenda_nome': pasto.fazenda.nome,
                'fazenda_id': pasto.fazenda.id,
                'area': float(pasto.area),
                'capacidade_ua': float(pasto.capacidade_ua),
                'coordenadas': pasto.coordenadas,
                'cor': cores_fazendas[pasto.fazenda.id]
            })
        
        context = {
            'pastos': pastos,
            'fazendas': fazendas,
            'fazenda_selecionada': fazenda_id,
            'pastos_json': json.dumps(pastos_json),
            'cores_fazendas': json.dumps(cores_fazendas)
        }
        
        return render(request, 'pastos/pasto_list.html', context)
    except Exception as e:
        messages.error(request, f'Erro ao carregar pastos: {str(e)}')
        return redirect('dashboard')

@login_required
def pasto_create(request):
    if request.method == 'POST':
        try:
            fazenda = get_object_or_404(Fazenda, pk=request.POST.get('fazenda'), usuario=request.user)
            variedade_capim_id = request.POST.get('variedade_capim')
            variedade_capim = None
            if variedade_capim_id:
                variedade_capim = get_object_or_404(VariedadeCapim, pk=variedade_capim_id)
            
            pasto = Pasto.objects.create(
                id_pasto=request.POST.get('id_pasto'),
                fazenda=fazenda,
                capacidade_ua=request.POST.get('capacidade_ua'),
                area=request.POST.get('area'),
                variedade_capim=variedade_capim,
                coordenadas=json.loads(request.POST.get('coordenadas', '[]'))
            )
            
            messages.success(request, 'Pasto criado com sucesso!')
            return redirect('pasto_list')
        except Exception as e:
            messages.error(request, f'Erro ao criar pasto: {str(e)}')
    
    fazenda_id = request.GET.get('fazenda')
    fazendas = Fazenda.objects.filter(usuario=request.user)
    variedades_capim = VariedadeCapim.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    
    # Configuração do mapa
    pastos_existentes = []
    centro_mapa = {'lat': -15.7801, 'lng': -47.9292, 'zoom': 4}  # Centro do Brasil como padrão
    
    if fazenda_id:
        try:
            fazenda = Fazenda.objects.get(pk=fazenda_id, usuario=request.user)
            pastos = Pasto.objects.filter(fazenda=fazenda)
            pastos_existentes = [{'coordenadas': pasto.coordenadas} for pasto in pastos]
            
            if pastos.exists():
                # Se existem pastos, usa a localização deles
                pasto = pastos.first()
                if pasto.coordenadas:
                    centro_mapa = {
                        'lat': pasto.coordenadas[0][0],
                        'lng': pasto.coordenadas[0][1],
                        'zoom': 15
                    }
            else:
                # Se não existem pastos, usa a localização da cidade/estado da fazenda
                try:
                    geolocator = Nominatim(user_agent="pecuaria_app")
                    location = geolocator.geocode(f"{fazenda.cidade}, {fazenda.estado}, Brazil", timeout=10)
                    if location:
                        centro_mapa = {
                            'lat': location.latitude,
                            'lng': location.longitude,
                            'zoom': 13
                        }
                except Exception:
                    pass  # Mantém o centro padrão em caso de erro
        except Fazenda.DoesNotExist:
            pass
    
    return render(request, 'pastos/pasto_form.html', {
        'fazendas': fazendas,
        'variedades_capim': variedades_capim,
        'fazenda_selecionada': fazenda_id,
        'pastos_existentes': json.dumps(pastos_existentes),
        'centro_mapa': json.dumps(centro_mapa)
    })

@login_required
def pasto_edit(request, pk):
    pasto = get_object_or_404(Pasto, pk=pk)
    
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            fazenda = get_object_or_404(Fazenda, pk=request.POST.get('fazenda'), usuario=request.user)
            variedade_capim_id = request.POST.get('variedade_capim')
            variedade_capim = None
            if variedade_capim_id:
                variedade_capim = get_object_or_404(VariedadeCapim, pk=variedade_capim_id)
            
            pasto.id_pasto = request.POST.get('id_pasto')
            pasto.fazenda = fazenda
            pasto.capacidade_ua = request.POST.get('capacidade_ua')
            pasto.area = request.POST.get('area')
            pasto.variedade_capim = variedade_capim
            pasto.coordenadas = json.loads(request.POST.get('coordenadas', '[]'))
            pasto.save()
            
            messages.success(request, 'Pasto atualizado com sucesso!')
            return redirect('pasto_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar pasto: {str(e)}')
            return redirect('pasto_edit', pk=pk)
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    variedades_capim = VariedadeCapim.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    
    # Obter os pastos existentes da mesma fazenda
    pastos_existentes = []
    if pasto.fazenda:
        outros_pastos = Pasto.objects.filter(fazenda=pasto.fazenda).exclude(pk=pk)
        for outro_pasto in outros_pastos:
            pastos_existentes.append({
                'id': outro_pasto.id,
                'coordenadas': outro_pasto.coordenadas
            })
    
    # Calcular o centro do mapa baseado nas coordenadas do pasto
    centro_mapa = None
    if pasto.coordenadas and len(pasto.coordenadas) > 0:
        lat_sum = sum(coord[0] for coord in pasto.coordenadas)
        lng_sum = sum(coord[1] for coord in pasto.coordenadas)
        centro_mapa = [lat_sum / len(pasto.coordenadas), lng_sum / len(pasto.coordenadas)]
    else:
        # Centro padrão se não houver coordenadas
        centro_mapa = [-15.788497, -47.879873]
    
    return render(request, 'pastos/pasto_form.html', {
        'pasto': pasto,
        'fazendas': fazendas,
        'variedades_capim': variedades_capim,
        'fazenda_selecionada': pasto.fazenda.id if pasto.fazenda else None,
        'pastos_existentes': json.dumps(pastos_existentes),
        'centro_mapa': json.dumps(centro_mapa),
        'coordenadas_existentes': json.dumps(pasto.coordenadas) if pasto.coordenadas else None
    })

@login_required
def pasto_delete(request, pk):
    pasto = get_object_or_404(Pasto, pk=pk)
    
    if request.method == 'POST':
        try:
            pasto.delete()
            messages.success(request, 'Pasto excluído com sucesso!')
            return redirect('pasto_list')
        except Exception as e:
            messages.error(request, f'Erro ao excluir pasto: {str(e)}')
    
    return render(request, 'pastos/pasto_delete.html', {'pasto': pasto})

@login_required
def get_cidade_coordenadas(request):
    try:
        fazenda_id = request.GET.get('fazenda_id')
        if not fazenda_id:
            return JsonResponse({'success': False, 'error': 'ID da fazenda não fornecido'})
        
        fazenda = get_object_or_404(Fazenda, pk=fazenda_id, usuario=request.user)
        
        # Buscar os pastos da fazenda
        pastos = Pasto.objects.filter(fazenda=fazenda)
        pastos_data = []
        
        for pasto in pastos:
            pastos_data.append({
                'id': pasto.id,
                'id_pasto': pasto.id_pasto,
                'nome': pasto.nome,
                'fazenda_nome': pasto.fazenda.nome,
                'fazenda_id': pasto.fazenda.id,
                'area': float(pasto.area),
                'capacidade_ua': float(pasto.capacidade_ua),
                'coordenadas': pasto.coordenadas,
                'cor': '#FF0000'  # Cor padrão para os pastos
            })
            
        # Obter coordenadas da cidade/estado
        geolocator = Nominatim(user_agent="pecuaria_app")
        location = geolocator.geocode(f"{fazenda.cidade}, {fazenda.estado}, Brazil", timeout=10)
        
        if location:
            return JsonResponse({
                'success': True,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'pastos': pastos_data
            })
        else:
            # Se não encontrar a localização, usar o centro do Brasil
            return JsonResponse({
                'success': True,
                'latitude': -15.7801,
                'longitude': -47.9292,
                'pastos': pastos_data
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def raca_list(request):
    racas = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/racas/raca_list.html', {'racas': racas})

@login_required
def raca_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        if nome:
            Raca.objects.create(nome=nome, usuario=request.user)
            messages.success(request, 'Raça criada com sucesso!')
            return redirect('raca_list')
    return render(request, 'configuracoes/racas/raca_form.html')

@login_required
def raca_edit(request, pk):
    raca = get_object_or_404(Raca, pk=pk, usuario=request.user)
    if request.method == 'POST':
        nome = request.POST.get('nome')
        if nome:
            raca.nome = nome
            raca.save()
            messages.success(request, 'Raça atualizada com sucesso!')
            return redirect('raca_list')
    return render(request, 'configuracoes/racas/raca_form.html', {'raca': raca})

@login_required
def raca_delete(request, pk):
    raca = get_object_or_404(Raca, pk=pk, usuario=request.user)
    raca.delete()
    messages.success(request, 'Raça excluída com sucesso!')
    return redirect('raca_list')

@login_required
def finalidade_lote_list(request):
    finalidades = FinalidadeLote.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/finalidades_lote/finalidade_lote_list.html', {'finalidades': finalidades})

@login_required
def finalidade_lote_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        if nome:
            try:
                FinalidadeLote.objects.create(nome=nome, usuario=request.user)
                messages.success(request, 'Finalidade de lote criada com sucesso!')
                return redirect('finalidade_lote_list')
            except IntegrityError:
                messages.error(request, 'Já existe uma finalidade com este nome para o seu usuário.')
    return render(request, 'configuracoes/finalidades_lote/finalidade_lote_form.html')

@login_required
def finalidade_lote_edit(request, pk):
    finalidade = get_object_or_404(FinalidadeLote, pk=pk, usuario=request.user)
    if request.method == 'POST':
        nome = request.POST.get('nome')
        if nome:
            try:
                finalidade.nome = nome
                finalidade.save()
                messages.success(request, 'Finalidade de lote atualizada com sucesso!')
                return redirect('finalidade_lote_list')
            except IntegrityError:
                messages.error(request, 'Já existe uma finalidade com este nome para o seu usuário.')
    return render(request, 'configuracoes/finalidades_lote/finalidade_lote_form.html', {'finalidade': finalidade})

@login_required
def finalidade_lote_delete(request, pk):
    finalidade = get_object_or_404(FinalidadeLote, pk=pk, usuario=request.user)
    if request.method == 'POST':
        finalidade.delete()
        messages.success(request, 'Finalidade de lote excluída com sucesso!')
        return redirect('finalidade_lote_list')
    return render(request, 'configuracoes/finalidades_lote/finalidade_lote_delete.html', {'finalidade': finalidade})

@login_required
def categoria_animal_list(request):
    categorias = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/categorias_animal/categoria_animal_list.html', {'categorias': categorias})

@login_required
def categoria_animal_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        sexo = request.POST.get('sexo')
        if nome and sexo:
            try:
                CategoriaAnimal.objects.create(nome=nome, sexo=sexo, usuario=request.user)
                messages.success(request, 'Categoria de animal criada com sucesso!')
                return redirect('categoria_animal_list')
            except:
                messages.error(request, 'Já existe uma categoria com este nome e sexo.')
    return render(request, 'configuracoes/categorias_animal/categoria_animal_form.html', {
        'sexo_choices': CategoriaAnimal.SEXO_CHOICES
    })

@login_required
def categoria_animal_edit(request, pk):
    categoria = get_object_or_404(CategoriaAnimal, pk=pk, usuario=request.user)
    if request.method == 'POST':
        nome = request.POST.get('nome')
        sexo = request.POST.get('sexo')
        if nome and sexo:
            try:
                categoria.nome = nome
                categoria.sexo = sexo
                categoria.save()
                messages.success(request, 'Categoria de animal atualizada com sucesso!')
                return redirect('categoria_animal_list')
            except:
                messages.error(request, 'Já existe uma categoria com este nome e sexo.')
    return render(request, 'configuracoes/categorias_animal/categoria_animal_form.html', {
        'categoria': categoria,
        'sexo_choices': CategoriaAnimal.SEXO_CHOICES
    })

@login_required
def categoria_animal_delete(request, pk):
    categoria = get_object_or_404(CategoriaAnimal, pk=pk, usuario=request.user)
    categoria.delete()
    messages.success(request, 'Categoria de animal excluída com sucesso!')
    return redirect('categoria_animal_list')

@login_required
def unidade_medida_list(request):
    unidades = UnidadeMedida.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('tipo', 'nome')
    return render(request, 'configuracoes/unidade_medida_list.html', {'unidades': unidades})

@login_required
def unidade_medida_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        sigla = request.POST.get('sigla')
        tipo = request.POST.get('tipo')
        descricao = request.POST.get('descricao')
        
        UnidadeMedida.objects.create(
            nome=nome,
            sigla=sigla,
            tipo=tipo,
            descricao=descricao,
            usuario=request.user
        )
        messages.success(request, 'Unidade de medida criada com sucesso!')
        return redirect('unidade-medida-list')
    
    return render(request, 'configuracoes/unidade_medida_form.html')

@login_required
def unidade_medida_edit(request, pk):
    unidade = get_object_or_404(UnidadeMedida, pk=pk)
    
    if request.method == 'POST':
        unidade.nome = request.POST.get('nome')
        unidade.sigla = request.POST.get('sigla')
        unidade.tipo = request.POST.get('tipo')
        unidade.descricao = request.POST.get('descricao')
        unidade.save()
        
        messages.success(request, 'Unidade de medida atualizada com sucesso!')
        return redirect('unidade-medida-list')
    
    return render(request, 'configuracoes/unidade_medida_form.html', {'unidade': unidade})

@login_required
def unidade_medida_delete(request, pk):
    unidade = get_object_or_404(UnidadeMedida, pk=pk)
    unidade.delete()
    messages.success(request, 'Unidade de medida excluída com sucesso!')
    return redirect('unidade-medida-list')

@login_required
def configuracoes(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'configuracoes/configuracoes.html')

@login_required
def motivo_morte_list(request):
    motivos = MotivoMorte.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/motivo_morte_list.html', {'motivos': motivos})

@login_required
def motivo_morte_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        MotivoMorte.objects.create(nome=nome, usuario=request.user)
        messages.success(request, 'Motivo de morte criado com sucesso!')
        return redirect('motivo-morte-list')
    return render(request, 'configuracoes/motivo_morte_form.html')

@login_required
def motivo_morte_edit(request, pk):
    motivo = get_object_or_404(MotivoMorte, pk=pk, usuario=request.user)
    if request.method == 'POST':
        motivo.nome = request.POST.get('nome')
        motivo.save()
        messages.success(request, 'Motivo de morte atualizado com sucesso!')
        return redirect('motivo-morte-list')
    return render(request, 'configuracoes/motivo_morte_form.html', {'motivo': motivo})

@login_required
def motivo_morte_delete(request, pk):
    motivo = get_object_or_404(MotivoMorte, pk=pk, usuario=request.user)
    motivo.delete()
    messages.success(request, 'Motivo de morte excluído com sucesso!')
    return redirect('motivo-morte-list')

@login_required
def variedade_capim_list(request):
    variedades = VariedadeCapim.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/variedade_capim_list.html', {'variedades': variedades})

@login_required
def variedade_capim_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        nome_cientifico = request.POST.get('nome_cientifico')
        VariedadeCapim.objects.create(
            nome=nome,
            nome_cientifico=nome_cientifico,
            usuario=request.user
        )
        messages.success(request, 'Variedade de capim criada com sucesso!')
        return redirect('variedade-capim-list')
    return render(request, 'configuracoes/variedade_capim_form.html')

@login_required
def variedade_capim_edit(request, pk):
    variedade = get_object_or_404(VariedadeCapim, pk=pk, usuario=request.user)
    if request.method == 'POST':
        variedade.nome = request.POST.get('nome')
        variedade.nome_cientifico = request.POST.get('nome_cientifico')
        variedade.save()
        messages.success(request, 'Variedade de capim atualizada com sucesso!')
        return redirect('variedade-capim-list')
    return render(request, 'configuracoes/variedade_capim_form.html', {'variedade': variedade})

@login_required
def variedade_capim_delete(request, pk):
    variedade = get_object_or_404(VariedadeCapim, pk=pk, usuario=request.user)
    variedade.delete()
    messages.success(request, 'Variedade de capim excluída com sucesso!')
    return redirect('variedade-capim-list')

@login_required
def categoria_custo_list(request):
    categorias = CategoriaCusto.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/categoria_custo_list.html', {'categorias': categorias})

@login_required
def categoria_custo_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tipo = request.POST.get('tipo')
        alocacao = request.POST.get('alocacao')
        CategoriaCusto.objects.create(
            nome=nome,
            tipo=tipo,
            alocacao=alocacao,
            usuario=request.user
        )
        messages.success(request, 'Categoria de custo criada com sucesso!')
        return redirect('categoria-custo-list')
    return render(request, 'configuracoes/categoria_custo_form.html')

@login_required
def categoria_custo_edit(request, pk):
    categoria = get_object_or_404(CategoriaCusto, pk=pk, usuario=request.user)
    if request.method == 'POST':
        categoria.nome = request.POST.get('nome')
        categoria.tipo = request.POST.get('tipo')
        categoria.alocacao = request.POST.get('alocacao')
        categoria.save()
        messages.success(request, 'Categoria de custo atualizada com sucesso!')
        return redirect('categoria-custo-list')
    return render(request, 'configuracoes/categoria_custo_form.html', {'categoria': categoria})

@login_required
def categoria_custo_delete(request, pk):
    categoria = get_object_or_404(CategoriaCusto, pk=pk, usuario=request.user)
    categoria.delete()
    messages.success(request, 'Categoria de custo excluída com sucesso!')
    return redirect('categoria-custo-list')

@login_required
def subcategoria_custo_list(request):
    subcategorias = SubcategoriaCusto.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, 'configuracoes/subcategoria_custo_list.html', {'subcategorias': subcategorias})

@login_required
def subcategoria_custo_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        categoria_id = request.POST.get('categoria')
        categoria = get_object_or_404(CategoriaCusto, pk=categoria_id, usuario=request.user)
        SubcategoriaCusto.objects.create(nome=nome, categoria=categoria, usuario=request.user)
        messages.success(request, 'Subcategoria de custo criada com sucesso!')
        return redirect('subcategoria-custo-list')
    categorias = CategoriaCusto.objects.filter(usuario=request.user)
    return render(request, 'configuracoes/subcategoria_custo_form.html', {'categorias': categorias})

@login_required
def subcategoria_custo_edit(request, pk):
    subcategoria = get_object_or_404(SubcategoriaCusto, pk=pk, usuario=request.user)
    if request.method == 'POST':
        subcategoria.nome = request.POST.get('nome')
        categoria_id = request.POST.get('categoria')
        subcategoria.categoria = get_object_or_404(CategoriaCusto, pk=categoria_id, usuario=request.user)
        subcategoria.save()
        messages.success(request, 'Subcategoria de custo atualizada com sucesso!')
        return redirect('subcategoria-custo-list')
    categorias = CategoriaCusto.objects.filter(usuario=request.user)
    return render(request, 'configuracoes/subcategoria_custo_form.html', {'subcategoria': subcategoria, 'categorias': categorias})

@login_required
def subcategoria_custo_delete(request, pk):
    subcategoria = get_object_or_404(SubcategoriaCusto, pk=pk, usuario=request.user)
    subcategoria.delete()
    messages.success(request, 'Subcategoria de custo excluída com sucesso!')
    return redirect('subcategoria-custo-list')

@login_required
def lote_list(request):
    lotes = Lote.objects.filter(usuario=request.user)
    return render(request, 'lotes/lote_list.html', {
        'lotes': lotes
    })

@login_required
def lote_create(request):
    if request.method == 'POST':
        lote = Lote(usuario=request.user)
        lote.id_lote = request.POST.get('id_lote')
        lote.data_criacao = request.POST.get('data_criacao')
        lote.finalidade = FinalidadeLote.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('finalidade'))
        lote.fazenda = get_object_or_404(Fazenda, id=request.POST.get('fazenda'), usuario=request.user)
        lote.save()
        
        messages.success(request, 'Lote criado com sucesso!')
        return redirect('lote_list')
    
    finalidades = FinalidadeLote.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    fazendas = Fazenda.objects.filter(usuario=request.user)
    
    return render(request, 'lotes/lote_form.html', {
        'titulo': 'Novo Lote',
        'finalidades': finalidades,
        'fazendas': fazendas
    })

@login_required
def lote_edit(request, pk):
    lote = get_object_or_404(Lote, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        lote.id_lote = request.POST.get('id_lote')
        lote.data_criacao = request.POST.get('data_criacao')
        lote.finalidade = FinalidadeLote.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('finalidade'))
        lote.fazenda = get_object_or_404(Fazenda, id=request.POST.get('fazenda'), usuario=request.user)
        lote.save()
        
        messages.success(request, 'Lote atualizado com sucesso!')
        return redirect('lote_list')
    
    finalidades = FinalidadeLote.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    fazendas = Fazenda.objects.filter(usuario=request.user)
    
    return render(request, 'lotes/lote_form.html', {
        'lote': lote,
        'titulo': 'Editar Lote',
        'finalidades': finalidades,
        'fazendas': fazendas
    })

@login_required
def lote_delete(request, pk):
    lote = get_object_or_404(Lote, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        lote.delete()
        messages.success(request, 'Lote excluído com sucesso!')
        return redirect('lote_list')
    
    return render(request, 'confirm_delete.html', {
        'object': lote,
        'title': 'Excluir Lote'
    })

@login_required
def lote_detail(request, lote_id):
    lote = get_object_or_404(Lote, id=lote_id, usuario=request.user)
    
    # Busca animais ativos no lote
    animais = Animal.objects.filter(lote=lote, situacao='ATIVO')
    print(f"Total de animais no lote: {animais.count()}")
    
    # Calcula estatísticas dos animais
    total_animais = animais.count()
    categorias = animais.values('categoria_animal__nome').annotate(
        total=Count('id')
    ).order_by('categoria_animal__nome')
    print(f"Distribuição por categorias: {list(categorias)}")
    
    # Calcula peso médio usando as últimas pesagens
    ultimas_pesagens = {}
    peso_total = 0
    for animal in animais:
        ultima_pesagem = Pesagem.objects.filter(
            animal=animal
        ).order_by('-data').first()
        if ultima_pesagem:
            ultimas_pesagens[animal.id] = ultima_pesagem
            peso_total += ultima_pesagem.peso
            print(f"Animal {animal.brinco_visual}: Última pesagem = {ultima_pesagem.peso}kg em {ultima_pesagem.data}")
    
    peso_medio_lote = peso_total / total_animais if total_animais > 0 else 0
    print(f"Peso médio do lote: {peso_medio_lote}kg")
    
    # Busca movimentações
    movimentacoes = MovimentacaoAnimal.objects.filter(
        Q(lote_origem=lote) | Q(lote_destino=lote)
    ).select_related('animal', 'lote_origem', 'lote_destino', 'pasto_origem', 'pasto_destino').order_by('-data_movimentacao')
    
    # Busca custos do lote
    hoje = timezone.now().date()
    custos = RateioCusto.objects.filter(
        animal__in=animais,
        item_despesa__despesa__data_emissao__lte=hoje
    ).values('item_despesa__categoria__tipo').annotate(
        total=Sum('valor')
    )
    
    custo_fixo = next((c['total'] for c in custos if c['item_despesa__categoria__tipo'] == 'fixo'), 0)
    custo_variavel = next((c['total'] for c in custos if c['item_despesa__categoria__tipo'] == 'variavel'), 0)
    custo_total = Decimal(str(custo_fixo)) + Decimal(str(custo_variavel))

    # Calcula custos por kg e por @
    custo_por_kg = 0
    custo_por_arroba = 0
    
    if peso_total > 0:
        custo_por_kg = float(custo_total / peso_total)
        # Calcula custo por @ (custo total / @ produzida)
        custo_por_arroba = float(custo_total / (peso_total / 15))

    # Calcula custos diários
    if total_animais > 0:
        custo_diario = custo_total / Decimal(str(total_animais))
        custo_variavel_diario = Decimal(str(custo_variavel)) / total_animais
        custo_fixo_diario = Decimal(str(custo_fixo)) / total_animais
    else:
        custo_diario = Decimal('0')
        custo_variavel_diario = Decimal('0')
        custo_fixo_diario = Decimal('0')

    # Informações de abate/venda
    valor_entrada = 0  # Definindo valor_entrada
    peso_final = 0
    valor_saida = 0
    arrobas_final = 0
    lucro = 0

    context = {
        'lote': lote,
        'total_animais': total_animais,
        'categorias': categorias,
        'peso_medio': peso_medio_lote,
        'movimentacoes': movimentacoes,
        'custo_fixo': custo_fixo,
        'custo_variavel': custo_variavel,
        'custo_total': custo_total,
        'custo_por_kg': custo_por_kg,
        'custo_por_arroba': custo_por_arroba,
        'custo_diario': custo_diario,
        'custo_variavel_diario': custo_variavel_diario,
        'custo_fixo_diario': custo_fixo_diario,
        'lucro': lucro,
        'arrobas_final': arrobas_final,
        'valor_saida': valor_saida
    }
    
    return render(request, 'core/lotes/lote_detail.html', context)

@login_required
def animal_list(request):
    from django.utils import timezone
    from django.db.models import Count, Q, Max, F, OuterRef, Subquery
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models.functions import Coalesce
    from .views_estatisticas import get_estatisticas_animais, get_estatisticas_detalhadas
    
    # Cache as consultas comuns
    user = request.user
    
    # Otimiza a subconsulta do peso mais recente
    ultima_pesagem = (
        Pesagem.objects
        .filter(animal=OuterRef('pk'))
        .order_by('-data')
        .values('peso')[:1]
    )
    
    # Query base otimizada
    queryset = (
        Animal.objects
        .filter(usuario=user)
        .select_related(
            'raca',
            'lote',
            'categoria_animal',
            'fazenda_atual',
            'pasto_atual'
        )
        .annotate(
            peso_atual=Coalesce(
                Subquery(ultima_pesagem),
                F('peso_entrada')
            )
        )
        .only(  # Seleciona apenas os campos necessários
            'brinco_visual',
            'brinco_eletronico',
            'data_nascimento',
            'situacao',
            'peso_entrada',
            'raca__nome',
            'lote__id_lote',
            'categoria_animal__nome',
            'fazenda_atual__nome',
            'pasto_atual__id_pasto',
            'pasto_atual__nome'
        )
        .defer('observacoes')  # Exclui campos grandes não utilizados
    )
    
    # Cache das opções de filtro
    categorias = (
        CategoriaAnimal.objects
        .filter(Q(usuario=None) | Q(usuario=user))
        .only('id', 'nome')
        .order_by('nome')
    )
    
    racas = (
        Raca.objects
        .filter(Q(usuario=None) | Q(usuario=user))
        .only('id', 'nome')
        .order_by('nome')
    )
    
    # Filtros otimizados
    filtros = {}
    
    if request.GET.get('fazenda'):
        filtros['fazenda'] = request.GET.get('fazenda')
        queryset = queryset.filter(fazenda_atual_id=filtros['fazenda'])
        
        # Cache dos lotes e pastos filtrados
        lotes = (
            Lote.objects
            .filter(fazenda_id=filtros['fazenda'], usuario=user)
            .only('id', 'id_lote')
        )
        pastos = (
            Pasto.objects
            .filter(fazenda_id=filtros['fazenda'], fazenda__usuario=user)
            .only('id', 'id_pasto', 'nome')
        )
    else:
        lotes = (
            Lote.objects
            .filter(usuario=user)
            .only('id', 'id_lote')
        )
        pastos = (
            Pasto.objects
            .filter(fazenda__usuario=user)
            .only('id', 'id_pasto', 'nome')
        )
    
    # Aplicar outros filtros
    if request.GET.get('lote'):
        filtros['lote'] = request.GET.get('lote')
        queryset = queryset.filter(lote_id=filtros['lote'])
    
    if request.GET.get('pasto'):
        filtros['pasto'] = request.GET.get('pasto')
        queryset = queryset.filter(pasto_atual_id=filtros['pasto'])
    
    if request.GET.get('categoria'):
        categoria_id = request.GET.get('categoria')
        filtros['categoria'] = int(categoria_id)
        queryset = queryset.filter(categoria_animal_id=filtros['categoria'])
    
    if request.GET.get('raca'):
        raca_id = request.GET.get('raca')
        filtros['raca'] = int(raca_id)
        queryset = queryset.filter(raca_id=filtros['raca'])
    
    if request.GET.get('brinco'):
        filtros['brinco'] = request.GET.get('brinco')
        queryset = queryset.filter(
            Q(brinco_visual__icontains=filtros['brinco']) |
            Q(brinco_eletronico__icontains=filtros['brinco'])
        )

    # Obtém as estatísticas usando queryset otimizado
    estatisticas = get_estatisticas_animais(request, queryset)
    
    # Obtém estatísticas detalhadas apenas se necessário
    estatisticas_detalhadas = get_estatisticas_detalhadas(request, queryset)

    # Paginação
    items_per_page = 50
    paginator = Paginator(queryset, items_per_page)
    page = request.GET.get('page')
    
    try:
        animais_paginados = paginator.page(page)
    except PageNotAnInteger:
        animais_paginados = paginator.page(1)
    except EmptyPage:
        animais_paginados = paginator.page(paginator.num_pages)

    # Cache da query de fazendas
    fazendas = (
        Fazenda.objects
        .filter(usuario=user)
        .only('id', 'nome')
    )

    context = {
        'animais': animais_paginados,
        'fazendas': fazendas,
        'lotes': lotes,
        'pastos': pastos,
        'categorias': categorias,
        'racas': racas,
        'filtros': filtros,
        'estatisticas': estatisticas,
        'estatisticas_detalhadas': estatisticas_detalhadas,
        'categorias_chart': estatisticas['categorias'],
        'total_ativos': estatisticas['stats']['ATIVO']['quantidade'],
        'total_vendidos': estatisticas['stats']['VENDIDO']['quantidade'],
        'total_mortos': estatisticas['stats']['MORTO']['quantidade'],
        'total_abatidos': estatisticas['stats']['ABATIDO']['quantidade'],
        'total_peso_kg': estatisticas['stats']['ATIVO']['peso_total'],
        'total_peso_arroba': estatisticas['stats']['ATIVO']['peso_arroba'],
        'active_tab': 'animais'
    }
    
    return render(request, 'animais/animal_list.html', context)

@login_required
def animal_create(request):
    if request.method == 'POST':
        try:
            # Dados básicos
            brinco_visual = request.POST.get('brinco_visual')
            brinco_eletronico = request.POST.get('brinco_eletronico')
            raca = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('raca'))
            data_nascimento = request.POST.get('data_nascimento')
            data_entrada = request.POST.get('data_entrada')
            lote = get_object_or_404(Lote, id=request.POST.get('lote'), usuario=request.user)
            categoria_animal = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('categoria_animal'))
            pasto_atual = get_object_or_404(Pasto, id=request.POST.get('pasto_atual'), fazenda=lote.fazenda)
            
            # Campos opcionais
            peso_entrada = request.POST.get('peso_entrada')
            if peso_entrada and peso_entrada.strip():
                peso_entrada = Decimal(peso_entrada.replace(',', '.'))
            else:
                peso_entrada = None
                
            valor_compra = request.POST.get('valor_compra')
            if valor_compra and valor_compra.strip():
                valor_compra = Decimal(valor_compra.replace(',', '.'))
            else:
                valor_compra = None
            
            animal = Animal.objects.create(
                brinco_visual=brinco_visual,
                brinco_eletronico=brinco_eletronico,
                raca=raca,
                data_nascimento=data_nascimento,
                data_entrada=data_entrada,
                lote=lote,
                categoria_animal=categoria_animal,
                pasto_atual=pasto_atual,
                peso_entrada=peso_entrada,
                valor_compra=valor_compra,
                fazenda_atual=lote.fazenda,
                usuario=request.user
            )
            
            messages.success(request, 'Animal cadastrado com sucesso!')
            return redirect('animal_list')
            
        except ValueError as e:
            messages.error(request, 'Erro: Verifique se os valores numéricos estão corretos')
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar animal: {str(e)}')
    
    # GET request
    lotes = Lote.objects.filter(usuario=request.user)
    pastos = []  # Inicialmente vazio, será preenchido via AJAX quando um lote for selecionado
    
    racas = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('nome')
    categorias = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('nome')
    
    return render(request, 'animais/animal_form.html', {
        'racas': racas,
        'categorias': categorias,
        'lotes': lotes,
        'pastos': pastos,
        'active_tab': 'animais'
    })

@login_required
def animal_edit(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            # Atualizando dados básicos
            animal.brinco_visual = request.POST.get('brinco_visual')
            animal.brinco_eletronico = request.POST.get('brinco_eletronico')
            animal.raca = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('raca'))
            animal.data_nascimento = request.POST.get('data_nascimento')
            animal.data_entrada = request.POST.get('data_entrada')
            animal.lote = get_object_or_404(Lote, id=request.POST.get('lote'), usuario=request.user)
            animal.categoria_animal = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=request.POST.get('categoria_animal'))
            animal.pasto_atual = get_object_or_404(Pasto, id=request.POST.get('pasto_atual'), fazenda=animal.fazenda_atual)
            
            # Campos opcionais com valores decimais
            peso_entrada = request.POST.get('peso_entrada')
            if peso_entrada and peso_entrada.strip():
                animal.peso_entrada = Decimal(peso_entrada.replace(',', '.'))
            else:
                animal.peso_entrada = None
                
            valor_compra = request.POST.get('valor_compra')
            if valor_compra and valor_compra.strip():
                animal.valor_compra = Decimal(valor_compra.replace(',', '.'))
            else:
                animal.valor_compra = None
            
            # Atualizar fazenda atual com base no lote
            animal.fazenda_atual = animal.lote.fazenda
            
            animal.save()
            messages.success(request, 'Animal atualizado com sucesso!')
            return redirect('animal_list')
            
        except ValueError as e:
            messages.error(request, 'Erro: Verifique se os valores numéricos estão corretos')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar animal: {str(e)}')
    
    # GET request
    racas = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('nome')
    lotes = Lote.objects.filter(usuario=request.user)
    categorias = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('nome')
    pastos = Pasto.objects.filter(fazenda=animal.fazenda_atual)
    
    context = {
        'animal': animal,
        'racas': racas,
        'categorias': categorias,
        'lotes': lotes,
        'pastos': pastos,
        'active_tab': 'animais'
    }
    return render(request, 'animais/animal_form.html', context)

@login_required
def animal_delete(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    
    try:
        animal.delete()
        messages.success(request, 'Animal excluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir animal: {str(e)}')
    
    return redirect('animal_list')

@login_required
def animal_detail(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    movimentacoes = animal.movimentacoes.all().order_by('-data_movimentacao')[:5]
    
    # Busca informações de abate e venda
    abate_animal = AbateAnimal.objects.filter(animal=animal).first()
    venda = VendaAnimal.objects.filter(animal=animal).first()
    
    # Calcula dias ativos - usa data de saída se existir, senão usa hoje
    data_entrada = animal.data_entrada
    if abate_animal:
        data_final = abate_animal.abate.data
    elif venda:
        data_final = venda.venda.data  # Acessando a data através do relacionamento com Venda
    else:
        data_final = timezone.now().date()
    
    dias_ativos = (data_final - data_entrada).days
    
    # Pega a última pesagem
    ultima_pesagem = animal.pesagens.order_by('-data').first()
    
    # Calcula peso atual e @ atual
    peso_atual = ultima_pesagem.peso if ultima_pesagem else None
    arroba_atual = None
    if peso_atual:
        # Se tem abate, usa o rendimento do abate, senão usa 50%
        rendimento = Decimal(str(abate_animal.rendimento)) / Decimal('100') if abate_animal else Decimal('0.5')
        arroba_atual = (Decimal(str(peso_atual)) * rendimento / Decimal('15'))
    
    # Calcula @ de entrada (sempre usa 50% de rendimento na entrada)
    peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else 0
    arroba_entrada = (peso_entrada * Decimal('0.5') / Decimal('15'))

    # Calcula ganho em @
    ganho_arroba = Decimal(str(arroba_atual - arroba_entrada)) if arroba_atual else None

    # Calcula o GMD (Ganho Médio Diário)
    gmd = 0
    ganho_peso = 0
    if peso_atual and animal.peso_entrada and dias_ativos > 0:
        ganho_peso = peso_atual - animal.peso_entrada
        gmd = round(ganho_peso / dias_ativos, 3)

    # Busca histórico de pesagens e manejos
    pesagens = animal.pesagens.all().order_by('-data')[:10]
    manejos_sanitarios = animal.manejos_sanitarios.all().order_by('-data')[:10]

    # Calcula custos
    rateios = RateioCusto.objects.filter(animal=animal)
    custos_fixos_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'fixo')
    custos_variaveis_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'variavel')
    custos_variaveis_totais += animal.custo_variavel or 0
    custos_total = Decimal(str(custos_fixos_totais)) + Decimal(str(custos_variaveis_totais))

    # Calcula custos por kg e por @
    custo_por_kg = 0
    custo_por_arroba = 0
    
    if animal.peso_entrada is not None and ultima_pesagem and ganho_arroba and ganho_arroba > 0:
        ganho_total = Decimal(str(peso_atual)) - Decimal(str(animal.peso_entrada))
        
        if custos_total > 0:
            # Calcula custo por kg (custo total / kg produzido)
            custo_por_kg = float(custos_total / ganho_total)
            # Calcula custo por @ (custo total / @ produzida)
            custo_por_arroba = float(custos_total / ganho_arroba)

    # Calcula custos diários
    if dias_ativos > 0:
        custo_diario = custos_total / Decimal(str(dias_ativos))
        custo_variavel_diario = Decimal(str(custos_variaveis_totais)) / dias_ativos
        custo_fixo_diario = Decimal(str(custos_fixos_totais)) / dias_ativos
    else:
        custo_diario = Decimal('0')
        custo_variavel_diario = Decimal('0')
        custo_fixo_diario = Decimal('0')

    # Informações de abate/venda
    valor_entrada = animal.valor_compra or 0  # Definindo valor_entrada
    
    # Busca informações de compra
    compra_animal = CompraAnimal.objects.filter(animal=animal).first()
    
    peso_final = 0
    valor_saida = 0
    arrobas_final = 0
    lucro = 0

    # Busca informações de abate
    if abate_animal:
        peso_final = abate_animal.peso_vivo
        valor_saida = abate_animal.valor_total
        # Calcula arrobas considerando o rendimento de carcaça
        rendimento_carcaca = Decimal(str(abate_animal.rendimento)) / Decimal('100')
        arrobas_final = (peso_final * rendimento_carcaca / Decimal('15')) if peso_final else 0
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    elif venda:
        peso_final = venda.peso_venda
        valor_saida = venda.valor_total
        arrobas_final = peso_final / Decimal('30')  # Venda usa rendimento padrão de 50%
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    else:
        peso_final = ultima_pesagem.peso if ultima_pesagem else peso_atual
        arrobas_final = peso_final / Decimal('30') if peso_final else 0

    context = {
        'animal': animal,
        'movimentacoes': movimentacoes,
        'dias_ativos': dias_ativos,
        'peso_atual': peso_atual,
        'arroba_atual': arroba_atual,
        'arroba_entrada': arroba_entrada,
        'ganho_arroba': ganho_arroba,
        'pesagens': pesagens,
        'manejos_sanitarios': manejos_sanitarios,
        'active_tab': 'animais',
        'gmd': gmd,
        # Novos campos de custos
        'custos_fixos_totais': custos_fixos_totais,
        'custos_variaveis_totais': custos_variaveis_totais,
        'custo_total': custos_total,
        'custo_por_kg': custo_por_kg,
        'custo_por_arroba': custo_por_arroba,
        'custo_diario': custo_diario,
        'custo_variavel_diario': custo_variavel_diario,
        'custo_fixo_diario': custo_fixo_diario,
        # Informações financeiras
        'lucro': lucro,
        'arrobas_final': arrobas_final,
        'valor_saida': valor_saida,
        'abate': abate_animal,
        'venda': venda,
        'compra': compra_animal
    }
    
    return render(request, 'animais/animal_detail.html', context)

@login_required
def movimentacao_create(request, animal_pk):
    animal = get_object_or_404(Animal, pk=animal_pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            tipo = request.POST.get('tipo')
            data_movimentacao = request.POST.get('data_movimentacao')
            destino_id = request.POST.get('destino')
            observacao = request.POST.get('observacao', '')
            
            # Validação básica
            if not tipo:
                raise ValueError('O tipo de movimentação é obrigatório')
            if not data_movimentacao:
                raise ValueError('A data da movimentação é obrigatória')
                
            # Validação específica por tipo
            if tipo == 'LOTE':
                if not destino_id:
                    raise ValueError('O lote de destino é obrigatório')
                    
                lote_origem = animal.lote
                lote_destino = get_object_or_404(Lote, pk=destino_id, usuario=request.user)
                
                if lote_origem == lote_destino:
                    raise ValueError('O lote de destino deve ser diferente do lote atual')
                
                movimentacao = MovimentacaoAnimal.objects.create(
                    animal=animal,
                    tipo=tipo,
                    data_movimentacao=data_movimentacao,
                    lote_origem=lote_origem,
                    lote_destino=lote_destino,
                    observacao=observacao,
                    usuario=request.user
                )
                
                # Atualiza o lote do animal
                animal.lote = lote_destino
                animal.save()
                
            elif tipo == 'PASTO':
                if not destino_id:
                    raise ValueError('O pasto de destino é obrigatório')
                    
                pasto_origem = animal.pasto_atual
                pasto_destino = get_object_or_404(Pasto, pk=destino_id, fazenda=animal.fazenda_atual)
                
                if pasto_origem == pasto_destino:
                    raise ValueError('O pasto de destino deve ser diferente do pasto atual')
                
                movimentacao = MovimentacaoAnimal.objects.create(
                    animal=animal,
                    tipo=tipo,
                    data_movimentacao=data_movimentacao,
                    pasto_origem=pasto_origem,
                    pasto_destino=pasto_destino,
                    observacao=observacao,
                    usuario=request.user
                )
                
                # Atualiza o pasto do animal
                animal.pasto_atual = pasto_destino
                animal.save()
                
            else:
                raise ValueError('Tipo de movimentação inválido')
            
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('animal_detail', pk=animal.pk)
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erro ao registrar movimentação: {str(e)}')
    
    # GET request - renderiza o formulário
    return render(request, 'animais/movimentacao_form.html', {
        'animal': animal,
        'lotes': Lote.objects.filter(usuario=request.user).exclude(pk=animal.lote.pk if animal.lote else None),
        'pastos': Pasto.objects.filter(fazenda=animal.fazenda_atual).exclude(pk=animal.pasto_atual.pk if animal.pasto_atual else None),
        'active_tab': 'animais'
    })

@login_required
def movimentacao_list(request, animal_pk):
    animal = get_object_or_404(Animal, pk=animal_pk, usuario=request.user)
    movimentacoes = animal.movimentacoes.all()
    
    return render(request, 'animais/movimentacao_list.html', {
        'animal': animal,
        'movimentacoes': movimentacoes,
        'active_tab': 'animais'
    })

@login_required
def pastos_por_lote(request, lote_id):
    try:
        # Buscar o lote e sua fazenda
        lote = get_object_or_404(Lote, id=lote_id, usuario=request.user)
        fazenda = lote.fazenda
        
        # Buscar os pastos da fazenda
        pastos = Pasto.objects.filter(fazenda=fazenda, fazenda__usuario=request.user)
        pastos_data = []
        
        for pasto in pastos:
            pastos_data.append({
                'id': pasto.id,
                'id_pasto': pasto.id_pasto,
                'nome': pasto.nome,
                'fazenda_nome': pasto.fazenda.nome,
                'fazenda_id': pasto.fazenda.id,
                'area': float(pasto.area),
                'capacidade_ua': float(pasto.capacidade_ua),
                'coordenadas': pasto.coordenadas,
                'cor': '#FF0000'  # Cor padrão para os pastos
            })
            
        return JsonResponse({
            'success': True,
            'pastos': pastos_data
        })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def pastos_por_fazenda(request, fazenda_id):
    try:
        # Buscar a fazenda
        fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)
        
        # Buscar os pastos da fazenda
        pastos = Pasto.objects.filter(fazenda=fazenda, fazenda__usuario=request.user)
        pastos_data = []
        
        for pasto in pastos:
            if pasto.coordenadas:  # Verificar se tem coordenadas
                try:
                    coordenadas = json.loads(pasto.coordenadas) if isinstance(pasto.coordenadas, str) else pasto.coordenadas
                    pastos_data.append({
                        'id': pasto.id,
                        'coordenadas': coordenadas,
                        'nome': pasto.nome
                    })
                except Exception as e:
                    print(f"Erro ao processar coordenadas do pasto {pasto.id_pasto}: {str(e)}")
                    continue
        
        # Obter coordenadas da cidade/estado
        geolocator = Nominatim(user_agent="pecuaria_app")
        location = geolocator.geocode(f"{fazenda.cidade}, {fazenda.estado}, Brazil", timeout=10)
        
        if location:
            return JsonResponse({
                'success': True,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'pastos': pastos_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Localização não encontrada'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def bulk_action(request):
    if request.method == 'POST':
        selected_animals = request.POST.getlist('selected_animals')
        action = request.POST.get('action')
        
        if not selected_animals:
            messages.error(request, 'Nenhum animal selecionado.')
            return redirect('animal_list')
            
        if action == 'edit':
            # Store selected animals in session for the bulk edit form
            request.session['selected_animals'] = selected_animals
            return redirect('bulk_edit')
        elif action == 'move':
            # Store selected animals in session for the bulk move form
            request.session['selected_animals'] = selected_animals
            return redirect('bulk_move')
        elif action == 'move_lot':
            # Store selected animals in session for the bulk move lot form
            request.session['selected_animals'] = selected_animals
            return redirect('bulk_move_lot')
        else:
            messages.error(request, 'Ação inválida selecionada.')
            return redirect('animal_list')
    
    return redirect('animal_list')

@login_required
def bulk_edit(request):
    selected_animals = request.session.get('selected_animals', [])
    if not selected_animals:
        messages.error(request, 'Nenhum animal selecionado para edição em massa.')
        return redirect('animal_list')
    
    animals = Animal.objects.filter(id__in=selected_animals, usuario=request.user)
    
    if request.method == 'POST':
        try:
            # Campos que podem ser editados em massa
            lote = request.POST.get('lote')
            categoria_animal = request.POST.get('categoria_animal')
            
            if lote:
                lote_obj = get_object_or_404(Lote, id=lote, usuario=request.user)
                animals.update(
                    lote=lote_obj,
                    fazenda_atual=lote_obj.fazenda
                )
            
            if categoria_animal:
                categoria_obj = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(id=categoria_animal)
                animals.update(categoria_animal=categoria_obj)
            
            messages.success(request, f'{len(animals)} animais atualizados com sucesso!')
            # Clear the session
            del request.session['selected_animals']
            return redirect('animal_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar animais: {str(e)}')
    
    context = {
        'animals': animals,
        'lotes': Lote.objects.filter(usuario=request.user),
        'categorias': CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).order_by('nome'),
        'active_tab': 'animais'
    }
    return render(request, 'animais/bulk_edit.html', context)

@login_required
def bulk_move(request):
    selected_animals = request.session.get('selected_animals', [])
    if not selected_animals:
        messages.error(request, 'Nenhum animal selecionado para movimentação em massa.')
        return redirect('animal_list')
    
    animals = Animal.objects.filter(id__in=selected_animals, usuario=request.user)
    
    if request.method == 'POST':
        try:
            pasto_destino = request.POST.get('pasto_destino')
            data_movimentacao = request.POST.get('data_movimentacao')
            motivo = request.POST.get('motivo', 'Movimentação em massa')
            
            if not pasto_destino or not data_movimentacao:
                raise ValueError('Pasto de destino e data de movimentação são obrigatórios.')
            
            pasto_obj = get_object_or_404(Pasto, id=pasto_destino)
            
            # Criar movimentação para cada animal
            for animal in animals:
                MovimentacaoAnimal.objects.create(
                    animal=animal,
                    tipo='PASTO',
                    pasto_origem=animal.pasto_atual,
                    pasto_destino=pasto_obj,
                    data_movimentacao=data_movimentacao,
                    motivo=motivo,
                    usuario=request.user
                )
                # Atualizar o pasto atual do animal
                animal.pasto_atual = pasto_obj
                animal.save()
            
            messages.success(request, f'{len(animals)} animais movimentados com sucesso!')
            # Clear the session
            del request.session['selected_animals']
            return redirect('animal_list')
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erro ao movimentar animais: {str(e)}')
    
    context = {
        'animals': animals,
        'pastos': Pasto.objects.filter(fazenda=animals.first().fazenda_atual),
        'active_tab': 'animais'
    }
    return render(request, 'animais/bulk_move.html', context)

@login_required
def bulk_move_lot(request):
    selected_animals = request.session.get('selected_animals', [])
    if not selected_animals:
        messages.error(request, 'Nenhum animal selecionado para movimentação de lote.')
        return redirect('animal_list')
    
    animals = Animal.objects.filter(id__in=selected_animals, usuario=request.user)
    
    if request.method == 'POST':
        try:
            lote_destino = request.POST.get('lote_destino')
            data_movimentacao = request.POST.get('data_movimentacao')
            mover_para_pasto = request.POST.get('mover_para_pasto') == 'on'
            pasto_destino = request.POST.get('pasto_destino') if mover_para_pasto else None
            
            if not lote_destino or not data_movimentacao:
                raise ValueError('Lote de destino e data de movimentação são obrigatórios.')
            
            if mover_para_pasto and not pasto_destino:
                raise ValueError('Pasto de destino é obrigatório quando a opção de mover para pasto está selecionada.')
            
            lote_obj = get_object_or_404(Lote, id=lote_destino, usuario=request.user)
            pasto_obj = get_object_or_404(Pasto, id=pasto_destino) if pasto_destino else None
            
            # Criar movimentação para cada animal
            for animal in animals:
                # Registrar movimentação de pasto se necessário
                if mover_para_pasto and pasto_obj:
                    MovimentacaoAnimal.objects.create(
                        animal=animal,
                        tipo='PASTO',
                        pasto_origem=animal.pasto_atual,
                        pasto_destino=pasto_obj,
                        data_movimentacao=data_movimentacao,
                        motivo=f"{motivo} - Movimentação de pasto devido à mudança de lote",
                        usuario=request.user
                    )
                
                # Registrar movimentação de lote
                MovimentacaoAnimal.objects.create(
                    animal=animal,
                    tipo='LOTE',
                    lote_origem=animal.lote,
                    lote_destino=lote_obj,
                    data_movimentacao=data_movimentacao,
                    motivo=motivo,
                    usuario=request.user
                )
                
                # Atualizar animal
                animal.lote = lote_obj
                animal.fazenda_atual = lote_obj.fazenda
                if mover_para_pasto and pasto_obj:
                    animal.pasto_atual = pasto_obj
                animal.save()
            
            messages.success(request, f'{len(animals)} animais movidos com sucesso para o lote {lote_obj.id_lote}!')
            # Clear the session
            del request.session['selected_animals']
            return redirect('animal_list')
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erro ao movimentar animais: {str(e)}')
    
    context = {
        'animals': animals,
        'lotes': Lote.objects.filter(usuario=request.user),
        'active_tab': 'animais'
    }
    return render(request, 'animais/bulk_move_lot.html', context)

@login_required
def download_planilha_modelo(request):
    wb = criar_planilha_modelo()
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=importacao_animais_modelo.xlsx'
    wb.save(response)
    return response

@login_required
def animal_import(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        try:
            # Ler o arquivo Excel
            df = pd.read_excel(
                request.FILES['arquivo'],
                parse_dates=['Data de Nascimento* (DD/MM/AAAA)', 'Data de Entrada* (DD/MM/AAAA)'],
                date_format='%d/%m/%Y'
            )
            
            # Validar cabeçalhos
            required_columns = [
                'Brinco Visual*',
                'Nome do Lote*',
                'Data de Nascimento* (DD/MM/AAAA)',
                'Data de Entrada* (DD/MM/AAAA)',
                'Raça*',
                'Categoria*',
                'Peso de Entrada (kg)*',
                'Valor de Compra (R$)*',
                'Pasto Atual*'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Colunas obrigatórias faltando: {", ".join(missing_columns)}'
                })
            
            # Validar dados
            errors = []
            success_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Validar brinco visual único
                    if Animal.objects.filter(brinco_visual=row['Brinco Visual*']).exists():
                        errors.append(f'Linha {index + 2}: Brinco Visual já existe')
                        continue
                    
                    # Validar brinco eletrônico único se fornecido
                    if pd.notna(row.get('Brinco Eletrônico')) and Animal.objects.filter(brinco_eletronico=row['Brinco Eletrônico']).exists():
                        errors.append(f'Linha {index + 2}: Brinco Eletrônico já existe')
                        continue
                    
                    # Validar lote
                    try:
                        lote = Lote.objects.get(id_lote=row['Nome do Lote*'], usuario=request.user)
                    except Lote.DoesNotExist:
                        errors.append(f'Linha {index + 2}: Lote não encontrado: {row["Nome do Lote*"]}')
                        continue
                    
                    # Validar pasto
                    try:
                        pasto = Pasto.objects.get(id_pasto=row['Pasto Atual*'], fazenda=lote.fazenda)
                    except Pasto.DoesNotExist:
                        errors.append(f'Linha {index + 2}: Pasto não encontrado: {row["Pasto Atual*"]}')
                        continue
                    
                    # Validar raça
                    try:
                        raca = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(nome=row['Raça*'])
                    except Raca.DoesNotExist:
                        errors.append(f'Linha {index + 2}: Raça não encontrada: {row["Raça*"]}')
                        continue
                        
                    # Validar categoria
                    try:
                        categoria = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(nome=row['Categoria*'])
                    except CategoriaAnimal.DoesNotExist:
                        errors.append(f'Linha {index + 2}: Categoria não encontrada: {row["Categoria*"]}')
                        continue
                    
                    # Converter datas
                    try:
                        data_nascimento = pd.to_datetime(row['Data de Nascimento* (DD/MM/AAAA)'])
                        data_entrada = pd.to_datetime(row['Data de Entrada* (DD/MM/AAAA)'])
                        
                        if pd.isna(data_nascimento) or pd.isna(data_entrada):
                            errors.append(f'Linha {index + 2}: Data inválida')
                            continue
                            
                        data_nascimento = data_nascimento.date()
                        data_entrada = data_entrada.date()
                    except Exception as e:
                        errors.append(f'Linha {index + 2}: Formato de data inválido - {str(e)}')
                        continue
                    
                    # Validar peso e valor
                    try:
                        peso_entrada = float(row['Peso de Entrada (kg)*'])
                        valor_compra = float(row['Valor de Compra (R$)*'])
                    except (ValueError, TypeError):
                        errors.append(f'Linha {index + 2}: Peso ou valor inválido')
                        continue
                    
                    # Criar o animal
                    animal = Animal(
                        brinco_visual=row['Brinco Visual*'],
                        brinco_eletronico=row.get('Brinco Eletrônico'),
                        raca=raca,
                        data_nascimento=data_nascimento,
                        data_entrada=data_entrada,
                        lote=lote,
                        categoria_animal=categoria,
                        peso_entrada=peso_entrada,
                        valor_compra=valor_compra,
                        fazenda_atual=lote.fazenda,
                        pasto_atual=pasto,
                        usuario=request.user
                    )
                    animal.save()
                    success_count += 1
                
                except Exception as e:
                    errors.append(f'Linha {index + 2}: Erro ao processar - {str(e)}')
            
            # Reportar resultados
            if success_count > 0:
                return JsonResponse({
                    'status': 'success',
                    'message': f'{success_count} animais importados com sucesso!',
                    'redirect_url': reverse('animal_list')
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Erros na importação: ' + '; '.join(errors)
                })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao processar arquivo: {str(e)}'
            })
    
    return render(request, 'animais/animal_import.html')

@login_required
def get_insumos(request):
    """Retorna a lista de insumos do usuário"""
    insumos = Insumo.objects.filter(usuario=request.user).values('id', 'nome')
    return JsonResponse(list(insumos), safe=False)

@login_required
def get_unidades_medida(request):
    unidades = UnidadeMedida.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return JsonResponse([{
        'id': u.id,
        'nome': u.nome,
        'sigla': u.sigla
    } for u in unidades], safe=False)

@login_required
def editar_pesagem(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
        
    try:
        pesagem = Pesagem.objects.get(pk=pk, usuario=request.user)
        
        data = request.POST.get('data')
        brinco = request.POST.get('animal')
        peso = request.POST.get('peso')
        
        if not all([data, brinco, peso]):
            return JsonResponse({
                'success': False,
                'message': 'Todos os campos são obrigatórios'
            }, status=400)
        
        try:
            animal = Animal.objects.get(Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco), usuario=request.user)
        except Animal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Animal com brinco {brinco} não encontrado'
            }, status=404)
        
        pesagem.data = data
        pesagem.animal = animal
        pesagem.peso = peso
        pesagem.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pesagem atualizada com sucesso'
        })
        
    except Pesagem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Pesagem não encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao atualizar pesagem: {str(e)}'
        }, status=500)

@login_required
def excluir_pesagem(request, pk):
    try:
        pesagem = Pesagem.objects.get(pk=pk, usuario=request.user)
        pesagem.delete()
        return JsonResponse({'success': True})
    except Pesagem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Pesagem não encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir pesagem: {str(e)}'
        }, status=500)

@login_required
def editar_manejo(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
        
    try:
        manejo = ManejoSanitario.objects.get(pk=pk, usuario=request.user)
        
        data = request.POST.get('data')
        brinco = request.POST.get('animal')
        tipo_manejo = request.POST.get('tipo_manejo')
        insumo = request.POST.get('insumo')
        dias_proximo = request.POST.get('dias_proximo_manejo')
        observacao = request.POST.get('observacao')
        
        if not all([data, brinco, tipo_manejo, insumo]):
            return JsonResponse({
                'success': False,
                'message': 'Os campos Data, Animal, Tipo de Manejo e Insumo são obrigatórios'
            }, status=400)
        
        try:
            animal = Animal.objects.get(Q(brinco_visual=brinco) | Q(brinco_eletronico=brinco), usuario=request.user)
        except Animal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Animal com brinco {brinco} não encontrado'
            }, status=404)
        
        manejo.data = data
        manejo.animal = animal
        manejo.tipo_manejo = tipo_manejo
        manejo.insumo = insumo
        manejo.dias_proximo_manejo = dias_proximo if dias_proximo else None
        manejo.observacao = observacao
        manejo.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Manejo atualizado com sucesso'
        })
        
    except ManejoSanitario.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Manejo não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao atualizar manejo: {str(e)}'
        }, status=500)

@login_required
def excluir_manejo(request, pk):
    try:
        manejo = ManejoSanitario.objects.get(pk=pk, usuario=request.user)
        manejo.delete()
        return JsonResponse({'success': True})
    except ManejoSanitario.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Manejo não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir manejo: {str(e)}'
        }, status=500)

@login_required
def manejo_list(request):
    try:
        manejos = ManejoSanitario.objects.filter(usuario=request.user).order_by('-data')
        pesagens = Pesagem.objects.filter(usuario=request.user).order_by('-data')
        
        context = {
            'manejos': manejos,
            'pesagens': pesagens,
            'title': 'Lista de Manejos e Pesagens'
        }
        return render(request, 'manejos/manejo_list.html', context)
    except Exception as e:
        messages.error(request, f'Erro ao carregar manejos: {str(e)}')
        return redirect('dashboard')

@login_required
def manejo_update(request, pk):
    manejo = get_object_or_404(ManejoSanitario, id=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            data = request.POST.get('data')
            animal_brinco = request.POST.get('animal')
            tipo_manejo = request.POST.get('tipo_manejo')
            insumo = request.POST.get('insumo')
            dias_proximo = request.POST.get('dias_proximo')
            observacao = request.POST.get('observacao')
            
            # Buscar o animal
            animal = get_object_or_404(Animal, Q(brinco_visual=animal_brinco) | Q(brinco_eletronico=animal_brinco), usuario=request.user)
            
            # Atualizar manejo
            manejo.data = data
            manejo.animal = animal
            manejo.tipo_manejo = tipo_manejo
            manejo.insumo = insumo
            manejo.dias_proximo_manejo = dias_proximo
            manejo.observacao = observacao
            manejo.save()
            
            return JsonResponse({'success': True})
        except Animal.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Animal não encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    # GET request - retornar dados do manejo
    return JsonResponse({
        'success': True,
        'manejo': {
            'id': manejo.id,
            'data': manejo.data.strftime('%Y-%m-%d'),
            'animal': manejo.animal.brinco_visual,
            'tipo_manejo': manejo.tipo_manejo,
            'insumo': manejo.insumo,
            'dias_proximo': manejo.dias_proximo_manejo,
            'observacao': manejo.observacao or ''
        }
    })

@login_required
def manejo_delete(request, pk):
    if request.method == 'DELETE':
        try:
            manejo = get_object_or_404(ManejoSanitario, id=pk, usuario=request.user)
            manejo.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def pesagem_update(request, pk):
    pesagem = get_object_or_404(Pesagem, id=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            data = request.POST.get('data')
            animal_brinco = request.POST.get('animal')
            peso = request.POST.get('peso')
            
            # Buscar o animal
            animal = get_object_or_404(Animal, Q(brinco_visual=animal_brinco) | Q(brinco_eletronico=animal_brinco), usuario=request.user)
            
            # Atualizar pesagem
            pesagem.data = data
            pesagem.animal = animal
            pesagem.peso = peso
            pesagem.save()
            
            return JsonResponse({'success': True})
        except Animal.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Animal não encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    # GET request - retornar dados da pesagem
    return JsonResponse({
        'success': True,
        'pesagem': {
            'id': pesagem.id,
            'data': pesagem.data.strftime('%Y-%m-%d'),
            'animal': pesagem.animal.brinco_visual,
            'peso': float(pesagem.peso)
        }
    })

@login_required
def pesagem_delete(request, pk):
    if request.method == 'DELETE':
        try:
            pesagem = get_object_or_404(Pesagem, id=pk, usuario=request.user)
            pesagem.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def maquinas_list(request):
    maquinas = Maquina.objects.filter(usuario=request.user)
    return render(request, 'fazendas/maquinas_list.html', {
        'maquinas': maquinas,
        'active_tab': 'fazendas'
    })

@login_required
def maquina_create(request):
    if request.method == 'POST':
        try:
            # Função para converter valor formatado em Decimal
            def converter_moeda_para_decimal(valor):
                if not valor:
                    return Decimal('0')
                # Remove o R$ e espaços
                valor = valor.replace('R$', '').strip()
                # Substitui ponto por nada (remove pontos de milhar) e vírgula por ponto
                valor = valor.replace('.', '').replace(',', '.')
                return Decimal(valor)

            data = {
                'id_maquina': request.POST.get('id_maquina'),
                'nome': request.POST.get('nome'),
                'valor_mercado': converter_moeda_para_decimal(request.POST.get('valor_mercado')),
                'valor_compra': converter_moeda_para_decimal(request.POST.get('valor_compra')),
                'valor_residual': converter_moeda_para_decimal(request.POST.get('valor_residual')),
                'vida_util': int(request.POST.get('vida_util')),
                'data_aquisicao': request.POST.get('data_aquisicao'),
                'fazenda_id': request.POST.get('fazenda'),
                'usuario': request.user
            }
            
            maquina = Maquina.objects.create(**data)
            messages.success(request, 'Máquina cadastrada com sucesso!')
            return redirect('maquinas_list')
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar máquina: {str(e)}')
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    print(f"Fazendas encontradas para o usuário {request.user}: {fazendas.count()}")
    return render(request, 'fazendas/maquina_form.html', {
        'fazendas': fazendas,
        'active_tab': 'fazendas',
        'titulo': 'Nova Máquina'
    })

@login_required
def maquina_edit(request, pk):
    maquina = get_object_or_404(Maquina, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        try:
            # Função para converter valor formatado em Decimal
            def converter_moeda_para_decimal(valor):
                if not valor:
                    return Decimal('0')
                # Remove o R$ e espaços
                valor = valor.replace('R$', '').strip()
                # Substitui ponto por nada (remove pontos de milhar) e vírgula por ponto
                valor = valor.replace('.', '').replace(',', '.')
                return Decimal(valor)

            maquina.id_maquina = request.POST.get('id_maquina')
            maquina.nome = request.POST.get('nome')
            maquina.valor_mercado = converter_moeda_para_decimal(request.POST.get('valor_mercado'))
            maquina.valor_compra = converter_moeda_para_decimal(request.POST.get('valor_compra'))
            maquina.valor_residual = converter_moeda_para_decimal(request.POST.get('valor_residual'))
            maquina.vida_util = int(request.POST.get('vida_util'))
            maquina.data_aquisicao = request.POST.get('data_aquisicao')
            maquina.fazenda_id = request.POST.get('fazenda')
            maquina.save()
            
            messages.success(request, 'Máquina atualizada com sucesso!')
            return redirect('maquinas_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar máquina: {str(e)}')
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'fazendas/maquina_form.html', {
        'maquina': maquina,
        'fazendas': fazendas,
        'active_tab': 'fazendas',
        'titulo': 'Editar Máquina'
    })

@login_required
def maquina_delete(request, pk):
    maquina = get_object_or_404(Maquina, pk=pk, usuario=request.user)
    try:
        maquina.delete()
        messages.success(request, 'Máquina excluída com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir máquina: {str(e)}')
    return redirect('maquinas_list')

@login_required
def maquina_detail(request, pk):
    maquina = get_object_or_404(Maquina, pk=pk, usuario=request.user)
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')
    
    # Query base
    despesas = ItemDespesa.objects.filter(maquina_destino=maquina).select_related('despesa', 'categoria', 'subcategoria')
    
    # Aplicar filtros
    if data_inicio:
        despesas = despesas.filter(despesa__data_emissao__gte=data_inicio)
    if data_fim:
        despesas = despesas.filter(despesa__data_emissao__lte=data_fim)
    if categoria:
        despesas = despesas.filter(categoria_id=categoria)
    if status:
        despesas = despesas.filter(despesa__status=status)
    
    # Calcular totais
    total_gasto = sum(despesa.valor_total for despesa in despesas)
    total_pendente = sum(despesa.valor_total for despesa in despesas if despesa.despesa.status == 'PENDENTE')
    total_pago = sum(despesa.valor_total for despesa in despesas if despesa.despesa.status == 'PAGO')
    
    # Buscar categorias para o filtro
    categorias = CategoriaCusto.objects.filter(
        id__in=despesas.values_list('categoria_id', flat=True).distinct()
    )
    
    context = {
        'maquina': maquina,
        'despesas': despesas,
        'total_gasto': total_gasto,
        'total_pendente': total_pendente,
        'total_pago': total_pago,
        'categorias': categorias,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'categoria': categoria,
            'status': status
        }
    }
    return render(request, 'fazendas/maquina_detail.html', context)

@login_required
def benfeitorias_list(request):
    benfeitorias = Benfeitoria.objects.filter(fazenda__usuario=request.user)
    return render(request, 'fazendas/benfeitorias_list.html', {
        'benfeitorias': benfeitorias,
        'active_tab': 'fazendas'
    })

@login_required
def benfeitoria_create(request):
    if request.method == 'POST':
        try:
            # Função para converter valor formatado em Decimal
            def converter_moeda_para_decimal(valor):
                if not valor:
                    return Decimal('0')
                # Remove o R$ e espaços
                valor = valor.replace('R$', '').strip()
                # Substitui ponto por nada (remove pontos de milhar) e vírgula por ponto
                valor = valor.replace('.', '').replace(',', '.')
                return Decimal(valor)

            data = {
                'id_benfeitoria': request.POST.get('id_benfeitoria'),
                'nome': request.POST.get('nome'),
                'valor_compra': converter_moeda_para_decimal(request.POST.get('valor_compra')),
                'valor_residual': converter_moeda_para_decimal(request.POST.get('valor_residual')),
                'vida_util': int(request.POST.get('vida_util')),
                'data_aquisicao': request.POST.get('data_aquisicao'),
                'fazenda_id': request.POST.get('fazenda'),
                'usuario_id': request.user.id  # Usando o ID do usuário atual
            }
            
            print("Data before coordinates:", data)  # Debug
            
            # Processa as coordenadas se existirem
            coordenadas = request.POST.get('coordenadas')
            print("Raw coordinates:", coordenadas)  # Debug
            
            if coordenadas:
                try:
                    data['coordenadas'] = json.loads(coordenadas)
                    print("Parsed coordinates:", data['coordenadas'])  # Debug
                except json.JSONDecodeError as e:
                    print("Error parsing coordinates:", str(e))  # Debug
                    messages.warning(request, 'Formato inválido das coordenadas. O ponto no mapa será ignorado.')
            
            print("Final data:", data)  # Debug
            
            benfeitoria = Benfeitoria.objects.create(**data)
            print("Benfeitoria created:", benfeitoria.id)  # Debug
            
            messages.success(request, 'Benfeitoria cadastrada com sucesso!')
            return redirect('benfeitorias_list')
        except Exception as e:
            print("Error creating benfeitoria:", str(e))  # Debug
            messages.error(request, f'Erro ao cadastrar benfeitoria: {str(e)}')
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'fazendas/benfeitoria_form.html', {
        'fazendas': fazendas,
        'active_tab': 'fazendas',
        'titulo': 'Nova Benfeitoria'
    })

@login_required
def benfeitoria_edit(request, pk):
    benfeitoria = get_object_or_404(Benfeitoria, pk=pk, fazenda__usuario=request.user)
    
    if request.method == 'POST':
        try:
            # Função para converter valor formatado em Decimal
            def converter_moeda_para_decimal(valor):
                if not valor:
                    return Decimal('0')
                # Remove o R$ e espaços
                valor = valor.replace('R$', '').strip()
                # Substitui ponto por nada (remove pontos de milhar) e vírgula por ponto
                valor = valor.replace('.', '').replace(',', '.')
                return Decimal(valor)

            benfeitoria.id_benfeitoria = request.POST.get('id_benfeitoria')
            benfeitoria.nome = request.POST.get('nome')
            benfeitoria.valor_compra = converter_moeda_para_decimal(request.POST.get('valor_compra'))
            benfeitoria.valor_residual = converter_moeda_para_decimal(request.POST.get('valor_residual'))
            benfeitoria.vida_util = int(request.POST.get('vida_util'))
            benfeitoria.data_aquisicao = request.POST.get('data_aquisicao')
            benfeitoria.fazenda_id = request.POST.get('fazenda')
            benfeitoria.save()
            
            # Processa as coordenadas
            coordenadas = request.POST.get('coordenadas')
            if coordenadas:
                try:
                    benfeitoria.coordenadas = json.loads(coordenadas)
                except json.JSONDecodeError:
                    messages.warning(request, 'Formato inválido das coordenadas. O ponto no mapa será ignorado.')
            
            messages.success(request, 'Benfeitoria atualizada com sucesso!')
            return redirect('benfeitorias_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar benfeitoria: {str(e)}')
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    return render(request, 'fazendas/benfeitoria_form.html', {
        'benfeitoria': benfeitoria,
        'fazendas': fazendas,
        'active_tab': 'fazendas',
        'titulo': 'Editar Benfeitoria'
    })

@login_required
def benfeitoria_delete(request, pk):
    benfeitoria = get_object_or_404(Benfeitoria, pk=pk, fazenda__usuario=request.user)
    
    if request.method == 'POST':
        benfeitoria.delete()
        messages.success(request, 'Benfeitoria excluída com sucesso!')
        return redirect('benfeitorias_list')
    
    return render(request, 'fazendas/benfeitoria_delete.html', {'benfeitoria': benfeitoria})

@login_required
def benfeitoria_detail(request, pk):
    benfeitoria = get_object_or_404(Benfeitoria, pk=pk, fazenda__usuario=request.user)
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')
    
    # Query base
    despesas = ItemDespesa.objects.filter(benfeitoria_destino=benfeitoria).select_related('despesa', 'categoria', 'subcategoria')
    
    # Aplicar filtros
    if data_inicio:
        despesas = despesas.filter(despesa__data_emissao__gte=data_inicio)
    if data_fim:
        despesas = despesas.filter(despesa__data_emissao__lte=data_fim)
    if categoria:
        despesas = despesas.filter(categoria_id=categoria)
    if status:
        despesas = despesas.filter(despesa__status=status)
    
    # Calcular totais
    total_gasto = sum(despesa.valor_total for despesa in despesas)
    total_pendente = sum(despesa.valor_total for despesa in despesas if despesa.despesa.status == 'PENDENTE')
    total_pago = sum(despesa.valor_total for despesa in despesas if despesa.despesa.status == 'PAGO')
    
    # Buscar categorias para o filtro
    categorias = CategoriaCusto.objects.filter(
        id__in=despesas.values_list('categoria_id', flat=True).distinct()
    )
    
    context = {
        'benfeitoria': benfeitoria,
        'despesas': despesas,
        'total_gasto': total_gasto,
        'total_pendente': total_pendente,
        'total_pago': total_pago,
        'categorias': categorias,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'categoria': categoria,
            'status': status
        },
        'active_tab': 'fazendas'
    }
    return render(request, 'fazendas/benfeitoria_detail.html', context)

@login_required
def compras_list(request):
    return render(request, 'financeiro/compras_list.html', {
        'active_tab': 'financeiro'
    })

@login_required
def abates_list(request):
    return render(request, 'financeiro/abates_list.html', {
        'active_tab': 'financeiro'
    })

@login_required
def contatos_list(request):
    return render(request, 'financeiro/contatos_list.html', {
        'active_tab': 'financeiro'
    })

@login_required
def contas_bancarias_list(request):
    return render(request, 'financeiro/contas_bancarias_list.html', {
        'active_tab': 'financeiro'
    })

# Views para Contas Bancárias
class ContaBancariaListView(LoginRequiredMixin, ListView):
    model = ContaBancaria
    template_name = 'financeiro/contas_bancarias_list.html'
    context_object_name = 'contas'

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calcular totais
        contas = self.get_queryset()
        context['total_contas'] = contas.count()
        context['total_saldo'] = Decimal('0.00')
        context['total_contas_ativas'] = contas.filter(ativa=True).count()
        context['total_contas_inativas'] = contas.filter(ativa=False).count()

        # Atualiza o saldo de cada conta com base nas movimentações
        for conta in contas:
            # Busca todas as movimentações da conta
            saldo = Decimal('0.00')
            
            # Despesas
            despesas = Despesa.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            saldo -= sum(despesa.valor_final() for despesa in despesas)
            
            # Vendas 
            vendas = Venda.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            saldo += sum(venda.valor_total for venda in vendas)
            
            # Compras
            compras = Compra.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            saldo -= sum(compra.valor_total for compra in compras)
            
            # Abates
            abates = Abate.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            saldo += sum(abate.valor_total for abate in abates)
            
            # Movimentações não operacionais
            nao_operacionais = MovimentacaoNaoOperacional.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for mov in nao_operacionais:
                if mov.tipo == 'entrada':
                    saldo += mov.valor
                else:  # saida
                    saldo -= mov.valor
            
            # Atualiza o saldo da conta em memória apenas
            conta.saldo = saldo
            
            # Adiciona ao total geral se a conta estiver ativa
            if conta.ativa:
                context['total_saldo'] += saldo
        
        return context

class ContaBancariaCreateView(LoginRequiredMixin, CreateView):
    model = ContaBancaria
    template_name = 'financeiro/conta_bancaria_form.html'
    fields = ['banco', 'agencia', 'conta', 'tipo', 'saldo', 'data_saldo', 'ativa', 'fazenda']
    success_url = reverse_lazy('contas_bancarias_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['fazenda'].queryset = Fazenda.objects.filter(usuario=self.request.user)
        return form

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class ContaBancariaUpdateView(LoginRequiredMixin, UpdateView):
    model = ContaBancaria
    template_name = 'financeiro/conta_bancaria_form.html'
    fields = ['banco', 'agencia', 'conta', 'tipo', 'saldo', 'data_saldo', 'ativa', 'fazenda']
    success_url = reverse_lazy('contas_bancarias_list')

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['fazenda'].queryset = Fazenda.objects.filter(usuario=self.request.user)
        return form

class ContaBancariaDeleteView(LoginRequiredMixin, DeleteView):
    model = ContaBancaria
    template_name = 'financeiro/conta_bancaria_delete.html'
    success_url = reverse_lazy('contas_bancarias_list')

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user)

class ContatoListView(LoginRequiredMixin, ListView):
    model = Contato
    template_name = 'contatos/contatos_list.html'
    context_object_name = 'contatos'

    def get_queryset(self):
        queryset = Contato.objects.filter(usuario=self.request.user)
        
        # Aplicar filtros
        nome = self.request.GET.get('nome')
        tipo = self.request.GET.get('tipo')
        cidade = self.request.GET.get('cidade')
        uf = self.request.GET.get('uf')
        
        if nome:
            queryset = queryset.filter(nome__icontains=nome)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if cidade:
            queryset = queryset.filter(cidade__icontains=cidade)
        if uf:
            queryset = queryset.filter(uf__iexact=uf)
        
        # Vendas (onde o contato é comprador)
        vendas_subquery = VendaAnimal.objects.filter(
            venda__comprador=OuterRef('pk')
        ).values('venda__comprador').annotate(
            total=Sum('valor_total', output_field=DecimalField(max_digits=10, decimal_places=2))
        ).values('total')

        # Compras (onde o contato é vendedor)
        compras_subquery = CompraAnimal.objects.filter(
            compra__vendedor=OuterRef('pk')
        ).values('compra__vendedor').annotate(
            total=Sum('valor_total', output_field=DecimalField(max_digits=10, decimal_places=2))
        ).values('total')

        # Despesas (onde o contato é fornecedor)
        despesas_subquery = ItemDespesa.objects.filter(
            despesa__contato=OuterRef('pk')
        ).values('despesa__contato').annotate(
            total=Sum(F('quantidade') * F('valor_unitario'))
        ).values('total')

        # Adicionar anotações
        queryset = queryset.annotate(
            total_vendas=Coalesce(
                Subquery(vendas_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ),
            total_compras=Coalesce(
                Subquery(compras_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ),
            total_despesas=Coalesce(
                Subquery(despesas_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            )
        )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calcular totais para os cards
        contatos = self.get_queryset()
        context['total_contatos'] = contatos.count()
        context['total_vendas'] = contatos.aggregate(
            total=Sum('total_vendas', output_field=DecimalField(max_digits=10, decimal_places=2))
        )['total'] or 0
        context['total_compras'] = contatos.aggregate(
            total=Sum('total_compras', output_field=DecimalField(max_digits=10, decimal_places=2))
        )['total'] or 0
        context['total_despesas'] = contatos.aggregate(
            total=Sum('total_despesas', output_field=DecimalField(max_digits=10, decimal_places=2))
        )['total'] or 0
        
        return context

class DespesaCreateView(LoginRequiredMixin, CreateView):
    model = Despesa
    template_name = 'financeiro/despesa_form.html'
    success_url = reverse_lazy('despesas_list')
    fields = ['forma_pagamento', 'numero_nf', 'data_emissao', 'data_vencimento', 'data_pagamento', 'contato', 'arquivo', 'conta_bancaria']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaCusto.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['unidades'] = UnidadeMedida.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['contatos'] = Contato.objects.filter(usuario=self.request.user, tipo='FO')
        context['contas_bancarias'] = ContaBancaria.objects.filter(usuario=self.request.user, ativa=True)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva a despesa
                self.object = form.save(commit=False)
                self.object.usuario = self.request.user
                
                # Define o status baseado na data de pagamento
                if self.object.data_pagamento:
                    self.object.status = 'PAGO'
                
                self.object.save()

                # Processa os itens da despesa
                itens_data = json.loads(self.request.POST.get('itens_despesa', '[]'))
                for item_data in itens_data:
                    categoria = CategoriaCusto.objects.get(
                        Q(id=item_data['categoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    subcategoria = SubcategoriaCusto.objects.get(
                        Q(id=item_data['subcategoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    
                    # Cria o item da despesa
                    item_despesa = ItemDespesa(
                        despesa=self.object,
                        categoria=categoria,
                        subcategoria=subcategoria,
                        quantidade=item_data['quantidade'],
                        valor_unitario=item_data['valor_unitario'],
                        valor_total=item_data['valor_total']
                    )
                    
                    # Define o destino apropriado baseado na alocação da categoria
                    if categoria.alocacao == 'fazenda':
                        item_despesa.fazenda_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'lote':
                        item_despesa.lote_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'maquina':
                        item_despesa.maquina_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'benfeitoria':
                        item_despesa.benfeitoria_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'pastagem':
                        item_despesa.pastagem_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'estoque':
                        item_despesa.fazenda_destino_id = item_data['destino_id']
                    
                    item_despesa.save()

                    # Se for um item de estoque, cria ou atualiza o insumo
                    if categoria.alocacao == 'estoque' and 'insumo' in item_data:
                        insumo_data = item_data['insumo']
                        if insumo_data['id']:
                            insumo = Insumo.objects.get(id=insumo_data['id'])
                        else:
                            insumo = Insumo.objects.create(
                                nome=insumo_data['nome'],
                                categoria=categoria,
                                subcategoria=subcategoria,
                                unidade_medida_id=insumo_data['unidade_medida_id'],
                                usuario=self.request.user
                            )
                        
                        # Cria a movimentação de estoque
                        from .views_estoque import criar_entrada_estoque_from_despesa
                        criar_entrada_estoque_from_despesa(self.object, item_despesa, insumo)

                messages.success(self.request, 'Despesa criada e registrada com sucesso!')
                return redirect(self.success_url)

        except CategoriaCusto.DoesNotExist:
            messages.error(self.request, 'Erro: Categoria de custo não encontrada.')
            return self.form_invalid(form)
        except SubcategoriaCusto.DoesNotExist:
            messages.error(self.request, 'Erro: Subcategoria de custo não encontrada.')
            return self.form_invalid(form)
        except json.JSONDecodeError:
            messages.error(self.request, 'Erro: Dados dos itens da despesa inválidos.')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Erro ao criar despesa: {str(e)}')
            return self.form_invalid(form)

@login_required
def despesa_detail(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk, usuario=request.user)
    itens = ItemDespesa.objects.filter(despesa=despesa)
    return render(request, 'financeiro/despesa_detail.html', {
        'active_tab': 'financeiro',
        'despesa': despesa,
        'itens': itens
    })

@login_required
def pagar_parcela(request, pk):
    parcela = get_object_or_404(ParcelaDespesa, id=pk)
    
    if request.method == 'POST':
        try:
            data_pagamento = request.POST.get('data_pagamento')
            multa_juros = Decimal(request.POST.get('multa_juros', '0'))
            desconto = Decimal(request.POST.get('desconto', '0'))
            
            # Atualiza a parcela
            parcela.data_pagamento = data_pagamento
            parcela.multa_juros = multa_juros
            parcela.desconto = desconto
            parcela.status = 'PAGO'  # Define explicitamente o status como PAGO
            parcela.save()  # O método save da parcela irá atualizar o status da despesa se necessário
            
            messages.success(request, 'Parcela paga com sucesso!')
            return redirect('despesa_detail', pk=parcela.despesa.id)
                
        except Exception as e:
            messages.error(request, f'Erro ao pagar parcela: {str(e)}')
            return redirect('despesa_detail', pk=parcela.despesa.id)
    
    return render(request, 'financeiro/pagar_parcela.html', {
        'parcela': parcela,
        'active_tab': 'financeiro'
    })

@login_required
def pagar_despesa(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        data_pagamento = request.POST.get('data_pagamento')
        multa_juros = Decimal(request.POST.get('multa_juros', '0'))
        desconto = Decimal(request.POST.get('desconto', '0'))
        observacao = request.POST.get('observacao', '')
        
        with transaction.atomic():
            despesa.data_pagamento = data_pagamento
            despesa.multa_juros = multa_juros
            despesa.desconto = desconto
            despesa.observacao = observacao
            despesa.status = 'PAGO'
            despesa.save()
            
            # Atualiza o status das parcelas
            parcelas = ParcelaDespesa.objects.filter(despesa=despesa)
            parcelas.update(status='PAGO')
            
            messages.success(request, 'Despesa paga com sucesso!')
            return redirect('despesa_detail', pk=despesa.id)
    return render(request, 'financeiro/pagar_despesa.html', {
        'despesa': despesa,
        'active_tab': 'financeiro'
    })

@login_required
def pasto_detail(request, pk):
    pasto = get_object_or_404(Pasto, pk=pk, fazenda__usuario=request.user)
    
    # Obtém o lote atual através dos animais que estão no pasto
    lote_atual = Lote.objects.filter(
        animal__pasto_atual=pasto,
        animal__situacao='ATIVO'
    ).first()
    
    # Conta quantos animais estão no pasto
    qtd_animais = Animal.objects.filter(
        pasto_atual=pasto,
        situacao='ATIVO'
    ).count()
    
    # Busca o último peso de cada animal no pasto
    from django.db.models import Max, F, ExpressionWrapper, DecimalField
    from django.db.models.functions import Coalesce

    # Subconsulta para pegar o último peso de cada animal
    ultima_pesagem = Pesagem.objects.filter(
        animal__pasto_atual=pasto,
        animal__situacao='ATIVO'
    ).values('animal').annotate(
        ultima_data=Max('data')
    ).values('animal', 'ultima_data')

    # Busca os pesos da última pesagem
    pesos = Pesagem.objects.filter(
        animal__in=[p['animal'] for p in ultima_pesagem],
        data__in=[p['ultima_data'] for p in ultima_pesagem]
    )
    
    # Soma total dos pesos
    soma_pesos = sum(peso.peso for peso in pesos)
    
    # Capacidade UA/ha (mantém o cálculo original para comparação)
    capacidade_ua_ha = round(Decimal(pasto.capacidade_ua) / Decimal(pasto.area), 2) if pasto.area else Decimal('0')
    
    # Calcula porcentagem de ocupação
    porcentagem_ocupacao = round((soma_pesos / capacidade_ua_ha * Decimal('100')), 1) if capacidade_ua_ha else Decimal('0')
    
    # Prepara dados para o mapa
    pasto_json = None
    if pasto.coordenadas:
        pasto_json = {
            'id': pasto.id,
            'id_pasto': pasto.id_pasto,
            'nome': pasto.nome,
            'fazenda_nome': pasto.fazenda.nome,
            'fazenda_id': pasto.fazenda.id,
            'area': float(pasto.area),
            'capacidade_ua': float(pasto.capacidade_ua),
            'coordenadas': pasto.coordenadas,
            'cor': '#2196F3'  # Azul
        }
    
    # Busca despesas relacionadas ao pasto
    despesas = ItemDespesa.objects.filter(
        despesa__usuario=request.user,
        pastagem_destino=pasto
    ).select_related(
        'despesa',
        'categoria',
        'subcategoria'
    ).order_by('-despesa__data_emissao')
    
    # Filtros para despesas
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')
    
    # Aplicar filtros se fornecidos
    if data_inicial:
        despesas = despesas.filter(despesa__data_emissao__gte=data_inicial)
    if data_final:
        despesas = despesas.filter(despesa__data_emissao__lte=data_final)
    if categoria:
        despesas = despesas.filter(categoria_id=categoria)
    if status:
        despesas = despesas.filter(despesa__status=status)
    
    # Calcular totais
    total_despesas = sum(item.valor_total for item in despesas)
    total_pagas = sum(item.valor_total for item in despesas if item.despesa.status == 'PAGO')
    total_pendentes = sum(item.valor_total for item in despesas if item.despesa.status == 'PENDENTE')
    total_vencidas = sum(item.valor_total for item in despesas if item.despesa.status == 'VENCIDO')
    total_vence_hoje = sum(item.valor_total for item in despesas if item.despesa.status == 'VENCE_HOJE')
    
    # Buscar categorias para o filtro
    categorias = CategoriaCusto.objects.filter(
        id__in=despesas.values_list('categoria_id', flat=True).distinct()
    )
    
    context = {
        'pasto': pasto,
        'lote_atual': lote_atual,
        'ua_ha_atual': soma_pesos,
        'capacidade_ua_ha': capacidade_ua_ha,
        'porcentagem_ocupacao': porcentagem_ocupacao,
        'qtd_animais': qtd_animais,
        'soma_pesos': soma_pesos,
        'ua_total': soma_pesos,
        'pasto_json': json.dumps([pasto_json], cls=DecimalJSONEncoder) if pasto_json else None,
        'despesas': despesas,
        'total_despesas': total_despesas,
        'total_pagas': total_pagas,
        'total_pendentes': total_pendentes,
        'total_vencidas': total_vencidas,
        'total_vence_hoje': total_vence_hoje,
        'filtros': {
            'data_inicial': data_inicial,
            'data_final': data_final,
            'categoria': categoria,
            'status': status
        }
    }
    
    return render(request, 'pastos/pasto_detail.html', context)

class DecimalJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class DespesaCreateView(LoginRequiredMixin, CreateView):
    model = Despesa
    template_name = 'financeiro/despesa_form.html'
    success_url = reverse_lazy('despesas_list')
    fields = ['forma_pagamento', 'numero_nf', 'data_emissao', 'data_vencimento', 'data_pagamento', 'contato', 'arquivo', 'conta_bancaria']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaCusto.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['unidades'] = UnidadeMedida.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['contatos'] = Contato.objects.filter(usuario=self.request.user, tipo='FO')
        context['contas_bancarias'] = ContaBancaria.objects.filter(usuario=self.request.user, ativa=True)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva a despesa
                self.object = form.save(commit=False)
                self.object.usuario = self.request.user
                
                # Define o status baseado na data de pagamento
                if self.object.data_pagamento:
                    self.object.status = 'PAGO'
                
                self.object.save()

                # Processa os itens da despesa
                itens_data = json.loads(self.request.POST.get('itens_despesa', '[]'))
                for item_data in itens_data:
                    categoria = CategoriaCusto.objects.get(
                        Q(id=item_data['categoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    subcategoria = SubcategoriaCusto.objects.get(
                        Q(id=item_data['subcategoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    
                    # Cria o item da despesa
                    item_despesa = ItemDespesa(
                        despesa=self.object,
                        categoria=categoria,
                        subcategoria=subcategoria,
                        quantidade=item_data['quantidade'],
                        valor_unitario=item_data['valor_unitario'],
                        valor_total=item_data['valor_total']
                    )
                    
                    # Define o destino apropriado baseado na alocação da categoria
                    if categoria.alocacao == 'fazenda':
                        item_despesa.fazenda_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'lote':
                        item_despesa.lote_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'maquina':
                        item_despesa.maquina_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'benfeitoria':
                        item_despesa.benfeitoria_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'pastagem':
                        item_despesa.pastagem_destino_id = item_data['destino_id']
                    elif categoria.alocacao == 'estoque':
                        item_despesa.fazenda_destino_id = item_data['destino_id']
                    
                    item_despesa.save()

                    # Se for um item de estoque, cria ou atualiza o insumo
                    if categoria.alocacao == 'estoque' and 'insumo' in item_data:
                        insumo_data = item_data['insumo']
                        if insumo_data['id']:
                            insumo = Insumo.objects.get(id=insumo_data['id'])
                        else:
                            insumo = Insumo.objects.create(
                                nome=insumo_data['nome'],
                                categoria=categoria,
                                subcategoria=subcategoria,
                                unidade_medida_id=insumo_data['unidade_medida_id'],
                                usuario=self.request.user
                            )
                        
                        # Cria a movimentação de estoque
                        from .views_estoque import criar_entrada_estoque_from_despesa
                        criar_entrada_estoque_from_despesa(self.object, item_despesa, insumo)

                messages.success(self.request, 'Despesa criada e registrada com sucesso!')
                return redirect(self.success_url)

        except CategoriaCusto.DoesNotExist:
            messages.error(self.request, 'Erro: Categoria de custo não encontrada.')
            return self.form_invalid(form)
        except SubcategoriaCusto.DoesNotExist:
            messages.error(self.request, 'Erro: Subcategoria de custo não encontrada.')
            return self.form_invalid(form)
        except json.JSONDecodeError:
            messages.error(self.request, 'Erro: Dados dos itens da despesa inválidos.')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Erro ao criar despesa: {str(e)}')
            return self.form_invalid(form)

@login_required
def fazenda_detail(request, pk):
    """
    Exibe os detalhes de uma fazenda específica
    """
    try:
        fazenda = get_object_or_404(Fazenda, pk=pk, usuario=request.user)
        
        # Carregar os pastos com suas coordenadas
        pastos = Pasto.objects.filter(fazenda=fazenda).select_related('variedade_capim')
        
        # Carregar outros dados relacionados
        lotes = Lote.objects.filter(fazenda=fazenda)
        maquinas = Maquina.objects.filter(fazenda=fazenda)
        benfeitorias = Benfeitoria.objects.filter(fazenda=fazenda)

        # Preparar dados dos pastos para o mapa
        pastos_json = []
        for pasto in pastos:
            pastos_json.append({
                'id': pasto.id,
                'id_pasto': pasto.id_pasto,
                'nome': pasto.nome,
                'fazenda_nome': pasto.fazenda.nome,
                'fazenda_id': pasto.fazenda.id,
                'area': float(pasto.area),
                'capacidade_ua': float(pasto.capacidade_ua),
                'coordenadas': pasto.coordenadas,
                'cor': '#3388ff'  # Azul
            })

        context = {
            'fazenda': fazenda,
            'lotes': lotes,
            'maquinas': maquinas,
            'benfeitorias': benfeitorias,
            'pastos_json': json.dumps(pastos_json)
        }
        return render(request, 'core/fazendas/fazenda_detail.html', context)
    except Exception as e:
        messages.error(request, f'Erro ao carregar detalhes da fazenda: {str(e)}')
        return redirect('fazenda_list')

@login_required
def animal_detail(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    movimentacoes = animal.movimentacoes.all().order_by('-data_movimentacao')[:5]
    
    # Busca informações de abate e venda
    abate_animal = AbateAnimal.objects.filter(animal=animal).first()
    venda = VendaAnimal.objects.filter(animal=animal).first()
    
    # Calcula dias ativos - usa data de saída se existir, senão usa hoje
    data_entrada = animal.data_entrada
    if abate_animal:
        data_final = abate_animal.abate.data
    elif venda:
        data_final = venda.venda.data  # Acessando a data através do relacionamento com Venda
    else:
        data_final = timezone.now().date()
    
    dias_ativos = (data_final - data_entrada).days
    
    # Pega a última pesagem
    ultima_pesagem = animal.pesagens.order_by('-data').first()
    
    # Calcula peso atual e @ atual
    peso_atual = ultima_pesagem.peso if ultima_pesagem else None
    arroba_atual = None
    if peso_atual:
        # Se tem abate, usa o rendimento do abate, senão usa 50%
        rendimento = Decimal(str(abate_animal.rendimento)) / Decimal('100') if abate_animal else Decimal('0.5')
        arroba_atual = (Decimal(str(peso_atual)) * rendimento / Decimal('15'))
    
    # Calcula @ de entrada (sempre usa 50% de rendimento na entrada)
    peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else 0
    arroba_entrada = (peso_entrada * Decimal('0.5') / Decimal('15'))

    # Calcula ganho em @
    ganho_arroba = Decimal(str(arroba_atual - arroba_entrada)) if arroba_atual else None

    # Calcula o GMD (Ganho Médio Diário)
    gmd = 0
    ganho_peso = 0
    if peso_atual and animal.peso_entrada and dias_ativos > 0:
        ganho_peso = peso_atual - animal.peso_entrada
        gmd = round(ganho_peso / dias_ativos, 3)

    # Busca histórico de pesagens e manejos
    pesagens = animal.pesagens.all().order_by('-data')[:10]
    manejos_sanitarios = animal.manejos_sanitarios.all().order_by('-data')[:10]

    # Calcula custos
    rateios = RateioCusto.objects.filter(animal=animal)
    custos_fixos_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'fixo')
    custos_variaveis_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'variavel')
    custos_variaveis_totais += animal.custo_variavel or 0
    custos_total = Decimal(str(custos_fixos_totais)) + Decimal(str(custos_variaveis_totais))

    # Calcula custos por kg e por @
    custo_por_kg = 0
    custo_por_arroba = 0
    
    if animal.peso_entrada is not None and ultima_pesagem and ganho_arroba and ganho_arroba > 0:
        ganho_total = Decimal(str(peso_atual)) - Decimal(str(animal.peso_entrada))
        
        if custos_total > 0:
            # Calcula custo por kg (custo total / kg produzido)
            custo_por_kg = float(custos_total / ganho_total)
            # Calcula custo por @ (custo total / @ produzida)
            custo_por_arroba = float(custos_total / ganho_arroba)

    # Calcula custos diários
    if dias_ativos > 0:
        custo_diario = custos_total / Decimal(str(dias_ativos))
        custo_variavel_diario = Decimal(str(custos_variaveis_totais)) / dias_ativos
        custo_fixo_diario = Decimal(str(custos_fixos_totais)) / dias_ativos
    else:
        custo_diario = Decimal('0')
        custo_variavel_diario = Decimal('0')
        custo_fixo_diario = Decimal('0')

    # Informações de abate/venda
    valor_entrada = animal.valor_compra or 0  # Definindo valor_entrada
    
    # Busca informações de compra
    compra_animal = CompraAnimal.objects.filter(animal=animal).first()
    
    peso_final = 0
    valor_saida = 0
    arrobas_final = 0
    lucro = 0

    # Busca informações de abate
    if abate_animal:
        peso_final = abate_animal.peso_vivo
        valor_saida = abate_animal.valor_total
        # Calcula arrobas considerando o rendimento de carcaça
        rendimento_carcaca = Decimal(str(abate_animal.rendimento)) / Decimal('100')
        arrobas_final = (peso_final * rendimento_carcaca / Decimal('15')) if peso_final else 0
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    elif venda:
        peso_final = venda.peso_venda
        valor_saida = venda.valor_total
        arrobas_final = peso_final / Decimal('30')  # Venda usa rendimento padrão de 50%
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    else:
        peso_final = ultima_pesagem.peso if ultima_pesagem else peso_atual
        arrobas_final = peso_final / Decimal('30') if peso_final else 0

    context = {
        'animal': animal,
        'movimentacoes': movimentacoes,
        'dias_ativos': dias_ativos,
        'peso_atual': peso_atual,
        'arroba_atual': arroba_atual,
        'arroba_entrada': arroba_entrada,
        'ganho_arroba': ganho_arroba,
        'pesagens': pesagens,
        'manejos_sanitarios': manejos_sanitarios,
        'active_tab': 'animais',
        'gmd': gmd,
        # Novos campos de custos
        'custos_fixos_totais': custos_fixos_totais,
        'custos_variaveis_totais': custos_variaveis_totais,
        'custo_total': custos_total,
        'custo_por_kg': custo_por_kg,
        'custo_por_arroba': custo_por_arroba,
        'custo_diario': custo_diario,
        'custo_variavel_diario': custo_variavel_diario,
        'custo_fixo_diario': custo_fixo_diario,
        # Informações financeiras
        'lucro': lucro,
        'arrobas_final': arrobas_final,
        'valor_saida': valor_saida,
        'abate': abate_animal,
        'venda': venda,
        'compra': compra_animal
    }
    
    return render(request, 'animais/animal_detail.html', context)

class DespesaUpdateView(LoginRequiredMixin, UpdateView):
    model = Despesa
    template_name = 'financeiro/despesa_form.html'
    fields = ['numero_nf', 'data_emissao', 'data_vencimento', 'contato', 'forma_pagamento', 'arquivo']
    success_url = reverse_lazy('despesas_list')

    def get_queryset(self):
        return Despesa.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class DespesaDeleteView(LoginRequiredMixin, DeleteView):
    model = Despesa
    template_name = 'financeiro/despesa_delete.html'
    success_url = reverse_lazy('despesas_list')

    def get_queryset(self):
        return Despesa.objects.filter(usuario=self.request.user)

@login_required
def get_subcategorias(request, categoria_id):
    try:
        # Primeiro verifica se a categoria pertence ao usuário
        categoria = CategoriaCusto.objects.get(
            Q(id=categoria_id) & (Q(usuario=request.user) | Q(usuario__isnull=True))
        )
        subcategorias = SubcategoriaCusto.objects.filter(
            Q(categoria=categoria) & (Q(usuario=request.user) | Q(usuario__isnull=True))
        )
        data = [{'id': sub.id, 'nome': sub.nome} for sub in subcategorias]
        return JsonResponse(data, safe=False)
    except CategoriaCusto.DoesNotExist:
        return JsonResponse({'error': 'Categoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_destinos(request):
    tipo_alocacao = request.GET.get('tipo_alocacao', '').lower()
    usuario = request.user
    
    if tipo_alocacao in ['fazenda', 'FAZENDA']:
        items = Fazenda.objects.filter(usuario=usuario)
        data = [{'id': item.id, 'nome': item.nome} for item in items]
    elif tipo_alocacao in ['lote', 'LOTE']:
        items = Lote.objects.filter(fazenda__usuario=usuario)
        return JsonResponse(list(items.values('id', 'id_lote')), safe=False)
    elif tipo_alocacao in ['maquina', 'MAQUINA']:
        items = Maquina.objects.filter(fazenda__usuario=usuario)
        data = [{'id': item.id, 'nome': f"{item.id_maquina} - {item.nome}"} for item in items]
    elif tipo_alocacao in ['benfeitoria', 'BENFEITORIA']:
        items = Benfeitoria.objects.filter(usuario=usuario)
        data = [{'id': item.id, 'nome': f"{item.id_benfeitoria} - {item.nome}"} for item in items]
    elif tipo_alocacao in ['pastagem', 'PASTAGEM']:
        items = Pasto.objects.filter(fazenda__usuario=usuario)
        return JsonResponse(list(items.values('id', 'id_pasto')), safe=False)
    elif tipo_alocacao in ['estoque', 'ESTOQUE']:
        items = Fazenda.objects.filter(usuario=usuario)
        data = [{'id': item.id, 'nome': item.nome} for item in items]
    else:
        data = []
    
    return JsonResponse(data, safe=False)

class DecimalJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class ContatoCreateView(LoginRequiredMixin, CreateView):
    model = Contato
    template_name = 'contatos/contato_form.html'
    fields = ['nome', 'tipo', 'telefone', 'email', 'cidade', 'uf']
    success_url = reverse_lazy('contatos_list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class ContatoUpdateView(LoginRequiredMixin, UpdateView):
    model = Contato
    template_name = 'contatos/contato_form.html'
    fields = ['nome', 'tipo', 'telefone', 'email', 'cidade', 'uf']
    success_url = reverse_lazy('contatos_list')

    def get_queryset(self):
        return Contato.objects.filter(usuario=self.request.user)

class ContatoDeleteView(LoginRequiredMixin, DeleteView):
    model = Contato
    template_name = 'contatos/contato_delete.html'
    success_url = reverse_lazy('contatos_list')

    def get_queryset(self):
        return Contato.objects.filter(usuario=self.request.user)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, Case, When, Value, CharField
from django.utils import timezone
from django.views.generic import ListView
from decimal import Decimal
from .models import Despesa, ItemDespesa, Fazenda, Contato


@login_required
def get_pastos_por_fazenda(request, fazenda_id):
    """Retorna lista de pastos de uma fazenda em formato JSON"""
    try:
        fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
        pastos = Pasto.objects.filter(fazenda=fazenda).values('id', 'nome')
        return JsonResponse(list(pastos), safe=False)
    except Fazenda.DoesNotExist:
        return JsonResponse([], safe=False)

@login_required
def get_lotes_por_fazenda(request, fazenda_id):
    """Retorna lista de lotes de uma fazenda em formato JSON"""
    try:
        fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
        lotes = Lote.objects.filter(fazenda_id=fazenda_id, usuario=request.user)
        return JsonResponse(list(lotes.values('id', 'id_lote')), safe=False)
    except Fazenda.DoesNotExist:
        return JsonResponse([], safe=False)

def get_estatisticas_animais(request, queryset=None):
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    
    # Se não receber um queryset, usa todos os animais do usuário
    if queryset is None:
        queryset = Animal.objects.filter(usuario=request.user)
    
    # Data atual e data há 12 meses atrás
    data_atual = timezone.now().date()
    data_12_meses = data_atual - timedelta(days=365)
    
    # Inicializa o dicionário com todos os status possíveis
    stats = {
        'ATIVO': {'quantidade': 0, 'variacao': 0},
        'VENDIDO': {'quantidade': 0, 'variacao': 0},
        'MORTO': {'quantidade': 0, 'variacao': 0},
        'ABATIDO': {'quantidade': 0, 'variacao': 0}
    }
    
    # Contagem atual
    contagem_atual = queryset.values('situacao').annotate(
        total=Count('id')
    )
    
    # Contagem há 12 meses
    contagem_anterior = queryset.filter(
        data_cadastro__lte=data_12_meses
    ).values('situacao').annotate(
        total=Count('id')
    )
    
    # Preenche as quantidades atuais
    for item in contagem_atual:
        situacao = item['situacao']
        stats[situacao]['quantidade'] = item['total']
    
    # Calcula as variações
    for item in contagem_anterior:
        situacao = item['situacao']
        qtd_anterior = item['total']
        qtd_atual = stats[situacao]['quantidade']
        
        if qtd_anterior > 0:
            variacao = ((qtd_atual - qtd_anterior) / qtd_anterior) * 100
            stats[situacao]['variacao'] = round(variacao, 1)
    
    return stats

def get_estatisticas_detalhadas(request, queryset=None):
    from django.db.models import Count, Sum, Q
    
    # Se não receber um queryset, usa todos os animais do usuário
    if queryset is None:
        queryset = Animal.objects.filter(usuario=request.user)
    
    # Inicializa o dicionário com todos os status possíveis
    stats = {
        'ATIVO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'VENDIDO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'MORTO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0},
        'ABATIDO': {'quantidade': 0, 'peso_total': 0, 'peso_arroba': 0}
    }
    
    # Contagem atual
    contagem_atual = queryset.values('situacao').annotate(
        total=Count('id'),
        peso_total=Sum('peso_atual'),
        peso_arroba=Sum(Coalesce('peso_atual', Value(0)) / Decimal('15'))
    )
    
    # Preenche as quantidades atuais
    for item in contagem_atual:
        situacao = item['situacao']
        stats[situacao]['quantidade'] = item['total']
        stats[situacao]['peso_total'] = item['peso_total']
        stats[situacao]['peso_arroba'] = item['peso_arroba']
    
    return stats

class ExtratoBancarioListView(LoginRequiredMixin, ListView):
    model = ExtratoBancario
    template_name = 'financeiro/extrato_bancario_list.html'
    context_object_name = 'movimentacoes'

    def get_queryset(self):
        from decimal import Decimal
        from datetime import datetime
        
        queryset = []
        conta_id = self.request.GET.get('conta')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        if conta_id:
            conta = ContaBancaria.objects.get(id=conta_id, usuario=self.request.user)
            
            # Calcula o saldo inicial
            if data_inicio:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                saldo = conta.calcular_saldo_em_data(data_inicio)
            else:
                saldo = conta.saldo

            # Busca despesas pagas
            despesas = Despesa.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for despesa in despesas:
                queryset.append({
                    'data': despesa.data_pagamento,
                    'descricao': f'Despesa - {despesa.contato}',
                    'tipo': 'saida',
                    'valor': despesa.valor_final(),
                    'referencia': f'Despesa #{despesa.id}'
                })
            
            # Busca vendas pagas
            vendas = Venda.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for venda in vendas:
                queryset.append({
                    'data': venda.data_pagamento,
                    'descricao': f'Venda - {venda.comprador}',
                    'tipo': 'entrada',
                    'valor': venda.valor_total,
                    'referencia': f'Venda #{venda.id}'
                })
            
            # Busca compras pagas
            compras = Compra.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for compra in compras:
                queryset.append({
                    'data': compra.data_pagamento,
                    'descricao': f'Compra - {compra.vendedor}',
                    'tipo': 'saida',
                    'valor': compra.valor_total,
                    'referencia': f'Compra #{compra.id}'
                })
            
            # Busca abates com pagamentos
            abates = Abate.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for abate in abates:
                queryset.append({
                    'data': abate.data_pagamento,
                    'descricao': f'Abate - {abate.comprador}',
                    'tipo': 'entrada',
                    'valor': abate.valor_total,
                    'referencia': f'Abate #{abate.id}'
                })
            
            # Busca movimentações não operacionais
            nao_operacionais = MovimentacaoNaoOperacional.objects.filter(
                usuario=self.request.user,
                conta_bancaria=conta,
                status='PAGO',
                data_pagamento__isnull=False
            )
            for mov in nao_operacionais:
                if mov.tipo == 'entrada':
                    queryset.append({
                        'data': mov.data_pagamento,
                        'descricao': f'Movimentação não operacional - Entrada',
                        'tipo': 'entrada',
                        'valor': mov.valor,
                        'referencia': f'Movimentação não operacional #{mov.id}'
                    })
                else:
                    queryset.append({
                        'data': mov.data_pagamento,
                        'descricao': f'Movimentação não operacional - Saída',
                        'tipo': 'saida',
                        'valor': mov.valor,
                        'referencia': f'Movimentação não operacional #{mov.id}'
                    })
            
            # Ordena por data
            queryset.sort(key=lambda x: x['data'])

            # Calcular saldos
            saldo = conta.saldo if data_inicio is None else conta.calcular_saldo_em_data(data_inicio)
            
            for mov in queryset:
                saldo_anterior = saldo
                if mov['tipo'] == 'entrada':
                    saldo += Decimal(str(mov['valor']))
                else:  # saida
                    saldo -= Decimal(str(mov['valor']))
                mov['saldo_anterior'] = saldo_anterior
                mov['saldo_atual'] = saldo

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona lista de contas para o dropdown (apenas contas ativas do usuário)
        context['contas'] = ContaBancaria.objects.filter(usuario=self.request.user, ativa=True)
        
        # Adiciona conta selecionada
        conta_id = self.request.GET.get('conta')
        if conta_id:
            context['conta_selecionada'] = ContaBancaria.objects.filter(usuario=self.request.user).get(id=conta_id)
        
        # Adiciona datas do filtro
        context['data_inicio'] = self.request.GET.get('data_inicio', '')
        context['data_fim'] = self.request.GET.get('data_fim', '')
        
        # Calcular totais
        movimentacoes = context['object_list']
        context['total_entradas'] = sum((Decimal(str(m['valor'])) for m in movimentacoes if m['tipo'] == 'entrada'), Decimal('0.00'))
        context['total_saidas'] = sum((Decimal(str(m['valor'])) for m in movimentacoes if m['tipo'] == 'saida'), Decimal('0.00'))
        
        # Calcular saldo no período
        if movimentacoes:
            context['saldo_inicial'] = movimentacoes[0]['saldo_anterior']
            context['saldo_final_periodo'] = movimentacoes[-1]['saldo_atual']
            context['saldo_periodo'] = context['saldo_final_periodo'] - context['saldo_inicial']
        else:
            context['saldo_inicial'] = context['conta_selecionada'].saldo if context.get('conta_selecionada') else Decimal('0.00')
            context['saldo_final_periodo'] = context['saldo_inicial']
            context['saldo_periodo'] = Decimal('0.00')
        
        return context

from django.http import JsonResponse
from .models import SubcategoriaCusto

def get_subcategorias_por_categoria(request, categoria_id):
    """
    Retorna uma lista de subcategorias para uma determinada categoria de custo.
    """
    try:
        subcategorias = SubcategoriaCusto.objects.filter(categoria_id=categoria_id).values('id', 'nome')
        return JsonResponse(list(subcategorias), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, Case, When, Value, CharField
from django.utils import timezone
from django.views.generic import ListView
from decimal import Decimal
from .models import Despesa, ItemDespesa, Fazenda, Contato

class DespesasListView(LoginRequiredMixin, ListView):
    model = Despesa
    template_name = 'financeiro/despesas_list.html'
    context_object_name = 'despesas'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(usuario=self.request.user)

        hoje = timezone.localdate()

        # Prefetch related para otimizar as queries
        queryset = queryset.prefetch_related(
            'itens__categoria',
            'itens__subcategoria',
            'itens__fazenda_destino',
            'itens__lote_destino',
            'itens__maquina_destino',
            'itens__benfeitoria_destino',
            'itens__pastagem_destino'
        ).select_related('contato').annotate(
            status_real=Case(
                When(status='PENDENTE', data_vencimento=hoje, then=Value('VENCE_HOJE')),
                When(status='PENDENTE', data_vencimento__lt=hoje, then=Value('VENCIDO')),
                default='status',
                output_field=CharField(),
            )
        )

        # Aplicar filtros
        filtros = {}

        # Filtro de fazenda
        fazenda = self.request.GET.get('fazenda')
        if fazenda:
            fazenda_query = (
                Q(itens__fazenda_destino_id=fazenda) |
                Q(itens__lote_destino__fazenda_id=fazenda) |
                Q(itens__maquina_destino__fazenda_id=fazenda) |
                Q(itens__benfeitoria_destino__fazenda_id=fazenda) |
                Q(itens__pastagem_destino__fazenda_id=fazenda)
            )
            queryset = queryset.filter(fazenda_query).distinct()
            filtros['fazenda'] = fazenda

        # Filtro de fornecedor
        contato = self.request.GET.get('contato')
        if contato:
            queryset = queryset.filter(contato_id=contato)
            filtros['contato'] = contato

        # Filtro de categoria
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(itens__categoria_id=categoria).distinct()
            filtros['categoria'] = categoria

        # Filtro de subcategoria
        subcategoria = self.request.GET.get('subcategoria')
        if subcategoria:
            queryset = queryset.filter(itens__subcategoria_id=subcategoria).distinct()
            filtros['subcategoria'] = subcategoria

        # Filtro de destino (pode ser qualquer tipo de destino)
        destino = self.request.GET.get('destino')
        if destino:
            destino_query = (
                Q(itens__fazenda_destino_id=destino) |
                Q(itens__lote_destino_id=destino) |
                Q(itens__maquina_destino_id=destino) |
                Q(itens__benfeitoria_destino_id=destino) |
                Q(itens__pastagem_destino_id=destino)
            )
            queryset = queryset.filter(destino_query).distinct()
            filtros['destino'] = destino

        # Filtro de status
        status = self.request.GET.get('status')
        if status:
            if status == 'VENCE_HOJE':
                hoje = timezone.localdate()
                queryset = queryset.filter(data_vencimento=hoje)
            else:
                queryset = queryset.filter(status=status)
            filtros['status'] = status

        # Filtro de data
        data_inicio = self.request.GET.get('data_inicio')
        if data_inicio:
            queryset = queryset.filter(data_emissao__gte=data_inicio)
            filtros['data_inicio'] = data_inicio

        data_fim = self.request.GET.get('data_fim')
        if data_fim:
            queryset = queryset.filter(data_emissao__lte=data_fim)
            filtros['data_fim'] = data_fim

        self.filtros = filtros

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona os filtros ao contexto
        context['filtros'] = self.filtros
        
        # Pega as fazendas do usuário primeiro
        fazendas_usuario = Fazenda.objects.filter(usuario=self.request.user)
        context['fazendas'] = fazendas_usuario
        
        # Adiciona as opções de filtro ao contexto
        context['fornecedores'] = Contato.objects.filter(usuario=self.request.user, tipo='FO')
        context['categorias'] = CategoriaCusto.objects.filter(Q(usuario__isnull=True))  # Alterado para buscar globais
        context['subcategorias'] = SubcategoriaCusto.objects.filter(Q(usuario__isnull=True))  # Alterado para buscar globais
        
        # Busca todos os possíveis destinos
        context['destinos'] = []
        
        # Adiciona fazendas
        for fazenda in fazendas_usuario:
            context['destinos'].append({
                'id': fazenda.id,
                'nome': fazenda.nome,
                'tipo': 'fazenda'
            })
        
        # Adiciona lotes (filtrando pela fazenda do usuário)
        lotes = Lote.objects.filter(fazenda__in=fazendas_usuario).select_related('fazenda')
        for lote in lotes:
            context['destinos'].append({
                'id': lote.id,
                'nome': f"Lote {lote.id_lote} - {lote.fazenda.nome}",
                'tipo': 'lote'
            })
        
        # Adiciona máquinas (filtrando pela fazenda do usuário)
        maquinas = Maquina.objects.filter(fazenda__in=fazendas_usuario).select_related('fazenda')
        for maquina in maquinas:
            context['destinos'].append({
                'id': maquina.id,
                'nome': f"{maquina.nome} - {maquina.fazenda.nome}",
                'tipo': 'maquina'
            })
        
        # Adiciona benfeitorias (filtrando pela fazenda do usuário)
        benfeitorias = Benfeitoria.objects.filter(fazenda__in=fazendas_usuario).select_related('fazenda')
        for benfeitoria in benfeitorias:
            context['destinos'].append({
                'id': benfeitoria.id,
                'nome': f"{benfeitoria.nome} - {benfeitoria.fazenda.nome}",
                'tipo': 'benfeitoria'
            })
        
        # Adiciona pastagens (filtrando pela fazenda do usuário)
        pastagens = Pasto.objects.filter(fazenda__in=fazendas_usuario).select_related('fazenda')
        for pastagem in pastagens:
            context['destinos'].append({
                'id': pastagem.id,
                'nome': f"{pastagem.nome} - {pastagem.fazenda.nome}",
                'tipo': 'pastagem'
            })
        
        # Calcula os totais por status
        totais_status = {
            'PAGO': {'valor': Decimal('0.00'), 'cor': 'success', 'icone': 'bi-check-circle-fill'},
            'PENDENTE': {'valor': Decimal('0.00'), 'cor': 'warning', 'icone': 'bi-clock-fill'},
            'VENCIDO': {'valor': Decimal('0.00'), 'cor': 'danger', 'icone': 'bi-exclamation-circle-fill'},
            'VENCE_HOJE': {'valor': Decimal('0.00'), 'cor': 'info', 'icone': 'bi-calendar-check-fill'}
        }
        
        hoje = timezone.localdate()
        
        for despesa in self.get_queryset():
            if despesa.status == 'PAGO':
                totais_status['PAGO']['valor'] += despesa.valor_final()
            elif despesa.status_real == 'VENCIDO':  # Usando status_real para vencidos
                totais_status['VENCIDO']['valor'] += despesa.valor_final()
            elif despesa.status_real == 'VENCE_HOJE':  # Usando status_real para vence hoje
                totais_status['VENCE_HOJE']['valor'] += despesa.valor_final()
            elif despesa.status == 'PENDENTE':  # Pendentes normais (não vencidos)
                totais_status['PENDENTE']['valor'] += despesa.valor_final()
        
        # Formata os valores para exibição
        for status in totais_status.values():
            status['valor_formatado'] = f"R$ {status['valor']:,.2f}"
        
        context['totais_status'] = totais_status
        
        return context

def redefinir_senha_view(request, token=None):
    """View para redefinição de senha"""
    context = {
        'token': token,
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_KEY': settings.SUPABASE_ANON_KEY,
    }
    return render(request, 'registration/redefinir_senha.html', context)