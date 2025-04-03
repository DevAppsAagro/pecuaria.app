from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta

from .models import ManejoSanitario, Pesagem, Animal

@login_required
def manejo_list(request):
    try:
        # Parâmetros de filtro e paginação
        page = request.GET.get('page', 1)
        dias = request.GET.get('dias', 30)  # Padrão: últimos 30 dias
        busca = request.GET.get('busca', '')
        
        try:
            dias = int(dias)
        except (ValueError, TypeError):
            dias = 30
            
        # Calcular data limite
        data_limite = datetime.now().date() - timedelta(days=dias)
        
        # Construir filtro base para manejos
        filtro_manejos = Q(usuario=request.user) & Q(data__gte=data_limite)
        
        # Adicionar filtro de busca se fornecido
        if busca:
            # Verificar se é um número (brinco) ou texto (nome do animal)
            filtro_manejos = filtro_manejos & (
                Q(animal__brinco_visual__icontains=busca) | 
                Q(animal__brinco_eletronico__icontains=busca)
            )
        
        # Buscar manejos com otimização usando select_related
        manejos = ManejoSanitario.objects.filter(
            filtro_manejos
        ).select_related(
            'animal', 'usuario'
        ).order_by('-data')
        
        # Construir filtro base para pesagens
        filtro_pesagens = Q(usuario=request.user) & Q(data__gte=data_limite)
        
        # Adicionar filtro de busca se fornecido
        if busca:
            filtro_pesagens = filtro_pesagens & (
                Q(animal__brinco_visual__icontains=busca) | 
                Q(animal__brinco_eletronico__icontains=busca)
            )
        
        # Buscar pesagens com otimização
        todas_pesagens = Pesagem.objects.filter(
            filtro_pesagens
        ).select_related(
            'animal'
        ).order_by('-data')
        
        # Dicionário para armazenar pesagens relacionadas aos manejos
        # Chave: (animal_id, data_formatada)
        pesagens_por_animal_data = {}
        
        # Processar pesagens e criar dicionário para acesso rápido
        for pesagem in todas_pesagens:
            # Formatar data para comparação (apenas ano, mês e dia)
            data_formatada = pesagem.data.strftime('%Y-%m-%d')
            chave = (pesagem.animal.id, data_formatada)
            pesagens_por_animal_data[chave] = pesagem
        
        # Associar pesagens aos manejos
        for manejo in manejos:
            # Formatar data para comparação
            data_formatada = manejo.data.strftime('%Y-%m-%d')
            chave = (manejo.animal.id, data_formatada)
            
            # Verificar se existe pesagem para o mesmo animal na mesma data
            if chave in pesagens_por_animal_data:
                manejo.pesagem_relacionada = pesagens_por_animal_data[chave]
                # Marcar esta pesagem como já associada
                pesagens_por_animal_data[chave].associada = True
            else:
                manejo.pesagem_relacionada = None
        
        # Filtrar pesagens que não foram associadas a nenhum manejo
        pesagens_sem_manejo = [p for p in todas_pesagens if not hasattr(p, 'associada')]
        
        # Paginação dos manejos
        paginator = Paginator(manejos, 50)  # 50 registros por página
        try:
            manejos_paginados = paginator.page(page)
        except PageNotAnInteger:
            manejos_paginados = paginator.page(1)
        except EmptyPage:
            manejos_paginados = paginator.page(paginator.num_pages)
            
        # Paginação das pesagens sem manejo
        paginator_pesagens = Paginator(pesagens_sem_manejo, 50)  # 50 registros por página
        try:
            pesagens_paginadas = paginator_pesagens.page(page)
        except PageNotAnInteger:
            pesagens_paginadas = paginator_pesagens.page(1)
        except EmptyPage:
            pesagens_paginadas = paginator_pesagens.page(paginator_pesagens.num_pages)
        
        # Renderizar o template inicial com os dados
        # Também vamos pré-renderizar o conteúdo da tabela para o carregamento inicial
        from django.template.loader import render_to_string
        html_content = render_to_string('manejos/manejo_table_content.html', {
            'manejos': manejos_paginados,
            'pesagens_sem_manejo': pesagens_paginadas,
            'dias': dias,
            'busca': busca
        }, request=request)
        
        context = {
            'manejos': manejos_paginados,
            'pesagens_sem_manejo': pesagens_paginadas,
            'title': 'Lista de Manejos e Pesagens',
            'dias': dias,
            'total_manejos': manejos.count(),
            'total_pesagens': todas_pesagens.count(),
            'busca': busca,
            'html_content': html_content
        }
        return render(request, 'manejos/manejo_list.html', context)
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        context = {
            'title': 'Lista de Manejos e Pesagens',
            'error_message': f'Erro ao carregar manejos: {str(e)}',
            'error_details': error_traceback,
            'dias': request.GET.get('dias', 30),
            'busca': request.GET.get('busca', ''),
            'total_manejos': 0,
            'total_pesagens': 0
        }
        return render(request, 'manejos/manejo_list.html', context)


@login_required
def manejos_json(request):
    """
    View para retornar dados de manejos em formato JSON para AJAX
    """
    from django.template.loader import render_to_string
    from django.http import JsonResponse
    
    try:
        # Parâmetros de filtro e paginação
        page = request.GET.get('page', 1)
        dias = request.GET.get('dias', 30)  # Padrão: últimos 30 dias
        busca = request.GET.get('busca', '')
        
        # Limitar o número máximo de dias para evitar sobrecarga
        try:
            dias = int(dias)
            if dias > 3650:  # Máximo de 10 anos
                dias = 3650
        except (ValueError, TypeError):
            dias = 30
            
        # Calcular data limite
        data_limite = datetime.now().date() - timedelta(days=dias)
        
        # Construir filtro base para manejos
        filtro_manejos = Q(usuario=request.user) & Q(data__gte=data_limite)
        
        # Adicionar filtro de busca se fornecido
        if busca:
            # Verificar se é um número (brinco) ou texto (nome do animal)
            filtro_manejos = filtro_manejos & (
                Q(animal__brinco_visual__icontains=busca) | 
                Q(animal__brinco_eletronico__icontains=busca)
            )
        
        # Buscar manejos com otimização usando select_related
        manejos = ManejoSanitario.objects.filter(
            filtro_manejos
        ).select_related(
            'animal', 'usuario'
        ).order_by('-data')[:500]  # Limitar a 500 registros
        
        # Construir filtro base para pesagens
        filtro_pesagens = Q(usuario=request.user) & Q(data__gte=data_limite)
        
        # Adicionar filtro de busca se fornecido
        if busca:
            filtro_pesagens = filtro_pesagens & (
                Q(animal__brinco_visual__icontains=busca) | 
                Q(animal__brinco_eletronico__icontains=busca)
            )
        
        # Buscar pesagens com otimização
        pesagens = Pesagem.objects.filter(
            filtro_pesagens
        ).select_related(
            'animal'
        ).order_by('-data')[:500]  # Limitar a 500 registros
        
        # Criar um dicionário para associar pesagens aos manejos do mesmo animal e data
        pesagens_dict = {}
        for pesagem in pesagens:
            key = (pesagem.animal.id, pesagem.data)
            pesagens_dict[key] = pesagem
        
        # Associar pesagens aos manejos
        for manejo in manejos:
            key = (manejo.animal.id, manejo.data)
            if key in pesagens_dict:
                manejo.pesagem_relacionada = pesagens_dict[key]
                # Remover a pesagem do dicionário para não duplicar
                del pesagens_dict[key]
            else:
                manejo.pesagem_relacionada = None
        
        # Pesagens restantes (sem manejo correspondente)
        pesagens_sem_manejo = list(pesagens_dict.values())
        
        # Paginação dos manejos
        paginator = Paginator(manejos, 50)  # 50 registros por página
        try:
            manejos_paginados = paginator.page(page)
        except PageNotAnInteger:
            manejos_paginados = paginator.page(1)
        except EmptyPage:
            manejos_paginados = paginator.page(paginator.num_pages)
            
        # Paginação das pesagens sem manejo
        paginator_pesagens = Paginator(pesagens_sem_manejo, 50)  # 50 registros por página
        try:
            pesagens_paginadas = paginator_pesagens.page(page)
        except PageNotAnInteger:
            pesagens_paginadas = paginator_pesagens.page(1)
        except EmptyPage:
            pesagens_paginadas = paginator_pesagens.page(paginator_pesagens.num_pages)
        
        context = {
            'manejos': manejos_paginados,
            'pesagens_sem_manejo': pesagens_paginadas,
            'dias': dias,
            'busca': busca
        }
        
        # Renderizar apenas o conteúdo da tabela
        html_content = render_to_string('manejos/manejo_table_content.html', context, request=request)
        
        # Retornar dados em formato JSON
        return JsonResponse({
            'html': html_content,
            'total_manejos': len(manejos),
            'total_pesagens': len(pesagens_sem_manejo),
            'current_page': manejos_paginados.number,
            'num_pages': paginator.num_pages
        })
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Erro na view manejos_json: {str(e)}\n{error_traceback}")
        return JsonResponse({'error': str(e)}, status=500)
