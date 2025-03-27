from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Fazenda, Pasto, Benfeitoria, Animal
import json
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Max
from django.contrib import messages
from decimal import Decimal
from django.conf import settings
import os
import uuid
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

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
def get_pastos(request, fazenda_id):
    try:
        print(f"Buscando pastos para fazenda {fazenda_id}")  # Debug
        fazenda = get_object_or_404(Fazenda, id=fazenda_id, usuario=request.user)
        pastos = Pasto.objects.filter(fazenda=fazenda)
        print(f"Encontrados {pastos.count()} pastos")  # Debug
        
        pastos_data = []
        for pasto in pastos:
            if not pasto.coordenadas:  # Pula pastos sem coordenadas
                continue
                
            # Conta os animais ativos neste pasto
            qtd_animais = Animal.objects.filter(
                pasto_atual=pasto,
                situacao='ATIVO'
            ).count()
            
            pasto_info = {
                'id': pasto.id,
                'nome': pasto.nome or f'Pasto {pasto.id_pasto}',
                'id_pasto': pasto.id_pasto,
                'area': float(pasto.area),  # Convertendo Decimal para float
                'coordenadas': json.loads(pasto.coordenadas) if isinstance(pasto.coordenadas, str) else pasto.coordenadas,
                'qtd_animais': qtd_animais
            }
            print(f"Dados do pasto {pasto.id}: {pasto_info}")  # Debug
            pastos_data.append(pasto_info)
        
        response_data = {
            'success': True,
            'pastos': pastos_data
        }
        print(f"Resposta: {response_data}")  # Debug
        return JsonResponse(response_data)
    except Exception as e:
        print(f"Erro ao buscar pastos: {str(e)}")  # Debug
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

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

@login_required
def fazenda_create(request):
    """Cria uma nova fazenda com suporte para upload de logo"""
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
        # Dados básicos da fazenda
        data = {
            'nome': request.POST.get('nome'),
            'arrendada': request.POST.get('arrendada') == 'on',
            'inscricao_estadual': request.POST.get('inscricao_estadual'),
            'cidade': request.POST.get('cidade'),
            'estado': request.POST.get('estado'),
            'area_total': Decimal(request.POST.get('area_total').replace(',', '.')),
            'usuario': request.user
        }
        
        # Se não for arrendada, adiciona os campos específicos
        if not data['arrendada']:
            data['valor_hectare'] = Decimal(request.POST.get('valor_hectare', '0').replace(',', '.'))
            data['custo_oportunidade'] = Decimal(request.POST.get('custo_oportunidade', '0').replace(',', '.'))
        
        # Cria a fazenda
        fazenda = Fazenda.objects.create(**data)
        
        # Processa o upload da logo, se fornecida
        logo_file = request.FILES.get('logo')
        if logo_file:
            try:
                # Criar nome único para o arquivo
                file_ext = os.path.splitext(logo_file.name)[1]
                file_name = f"{uuid.uuid4()}{file_ext}"
                
                # Inicializar cliente Supabase com a chave de serviço
                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                
                # Imprimir informações de depuração
                print(f"Supabase URL: {settings.SUPABASE_URL}")
                print(f"Usando chave de serviço para upload")
                print(f"Bucket: logofazenda")
                print(f"File name: {file_name}")
                
                # Upload do arquivo
                result = supabase.storage.from_('logofazenda').upload(
                    file_name,
                    logo_file.read(),
                    {"content-type": logo_file.content_type}
                )
                
                # Gerar URL pública
                public_url = supabase.storage.from_('logofazenda').get_public_url(file_name)
                
                if public_url:
                    fazenda.logo_url = public_url
                    fazenda.save()
                else:
                    messages.warning(request, 'Não foi possível fazer o upload da logo. A fazenda foi criada sem logo.')
            except Exception as e:
                messages.error(request, f'Erro ao fazer upload da logo: {str(e)}')
                print(f"Erro detalhado: {e}")
        
        messages.success(request, 'Fazenda cadastrada com sucesso!')
        return redirect('fazenda_list')
    
    return render(request, 'fazendas/fazenda_form.html', {
        'titulo': 'Nova Fazenda',
        'estados': ESTADOS_BRASIL
    })

@login_required
def fazenda_edit(request, pk):
    """Edita uma fazenda existente com suporte para upload/remoção de logo"""
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
    
    fazenda = get_object_or_404(Fazenda, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        # Atualiza os dados básicos
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
        
        # Processa a logo
        logo_file = request.FILES.get('logo')
        remover_logo = request.POST.get('remover_logo') == 'on'
        
        # Se o usuário marcou para remover a logo
        if remover_logo and fazenda.logo_url:
            try:
                # Extrair nome do arquivo da URL
                old_file_name = fazenda.logo_url.split('/')[-1]
                old_path = f"{old_file_name}"
                
                # Inicializar cliente Supabase
                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                
                # Remover arquivo
                supabase.storage.from_('logofazenda').remove([old_path])
                
                # Limpar URL da logo
                fazenda.logo_url = None
            except Exception as e:
                messages.warning(request, f'Não foi possível remover a logo atual: {str(e)}')
        
        # Se o usuário enviou uma nova logo
        elif logo_file:
            try:
                # Remover logo antiga se existir
                if fazenda.logo_url:
                    try:
                        # Extrair nome do arquivo da URL
                        old_file_name = fazenda.logo_url.split('/')[-1]
                        old_path = f"{old_file_name}"
                        
                        # Remover arquivo antigo
                        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                        supabase.storage.from_('logofazenda').remove([old_path])
                    except Exception as e:
                        logger.error(f"Erro ao remover logo antiga: {str(e)}")
                
                # Criar nome único para o arquivo
                file_ext = os.path.splitext(logo_file.name)[1]
                file_name = f"{uuid.uuid4()}{file_ext}"
                
                # Inicializar cliente Supabase
                supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                
                # Imprimir informações de depuração
                print(f"Supabase URL: {settings.SUPABASE_URL}")
                print(f"Usando chave de serviço para upload")
                print(f"Bucket: logofazenda")
                print(f"File name: {file_name}")
                
                # Upload do arquivo
                result = supabase.storage.from_('logofazenda').upload(
                    file_name,
                    logo_file.read(),
                    {"content-type": logo_file.content_type}
                )
                
                # Gerar URL pública
                public_url = supabase.storage.from_('logofazenda').get_public_url(file_name)
                
                if public_url:
                    fazenda.logo_url = public_url
                else:
                    messages.warning(request, 'Não foi possível fazer o upload da nova logo.')
            except Exception as e:
                messages.error(request, f'Erro ao fazer upload da logo: {str(e)}')
        
        fazenda.save()
        messages.success(request, 'Fazenda atualizada com sucesso!')
        return redirect('fazenda_list')
    
    return render(request, 'fazendas/fazenda_form.html', {
        'titulo': 'Editar Fazenda',
        'fazenda': fazenda,
        'estados': ESTADOS_BRASIL
    })
