from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import date

from .models import Despesa, ItemDespesa, Fazenda, Contato, Animal, ManejoReproducao

@login_required
def debug_reprodutivo(request, animal_id=66):
    """View especial para depuração dos dados reprodutivos do animal 66"""
    # Recuperar animal
    animal = Animal.objects.get(pk=animal_id)
    
    # Consulta SQL direta para manejo reprodutivo
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM core_manejoreproducao WHERE animal_id = %s
        """, [animal_id])
        manejos_raw = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        manejos_sql = [dict(zip(columns, row)) for row in manejos_raw]
    
    # Consulta SQL direta para filhos
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM core_animal WHERE mae_id = %s
        """, [animal_id])
        filhos_raw = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        filhos_sql = [dict(zip(columns, row)) for row in filhos_raw]
    
    # Criar dados reprodutivos manualmente para o animal 66
    manejos_reprodutivos = [{
        'id': 1,
        'estacao_monta': 'Estação 2025',
        'data_concepcao': date(2025, 3, 12),
        'previsao_parto': date(2025, 12, 12),
        'diagnostico': 'PRENHE',
        'get_diagnostico_display': lambda: 'Prenhe',
        'data_diagnostico': date(2025, 4, 15),
        'resultado': 'NASCIMENTO',
        'get_resultado_display': lambda: 'Nascimento',
        'data_resultado': date(2025, 12, 15),
        'observacao': 'Manejo criado para debug'
    }]
    
    filhos = [{
        'id': 76,
        'brinco_visual': 'BZ001',
        'data_nascimento': date(2025, 12, 15),
        'raca': type('Raca', (), {'nome': 'Nelore'}),
        'categoria_animal': type('Categoria', (), {'get_sexo_display': lambda: 'Macho'}),
        'peso_entrada': 35,
        'pai': None
    }]
    
    bezerros_organizados = [{
        'estacao': 'Estação de Monta 2025',
        'bezerros': filhos
    }]
    
    context = {
        'animal': animal,
        'manejos_reprodutivos': manejos_reprodutivos,
        'filhos': filhos,
        'bezerros_organizados': bezerros_organizados,
        'manejos_sql': manejos_sql,
        'filhos_sql': filhos_sql
    }
    
    return render(request, 'animais/debug.html', context)


class DespesasListViewDebug(LoginRequiredMixin, ListView):
    model = Despesa
    template_name = 'financeiro/despesas_list.html'
    context_object_name = 'despesas'
    
    def get_queryset(self):
        print("\n=== DEBUG: Iniciando get_queryset ===")
        queryset = Despesa.objects.filter(usuario=self.request.user)
        print(f"Despesas iniciais: {queryset.count()}")
        
        # Filtro de fazenda
        fazenda_id = self.request.GET.get('fazenda')
        print(f"Filtro fazenda_id: {fazenda_id}")
        if fazenda_id:
            itens_fazenda = ItemDespesa.objects.filter(
                Q(categoria__alocacao='fazenda', fazenda_destino_id=fazenda_id) |
                Q(categoria__alocacao='lote', lote_destino__fazenda_id=fazenda_id) |
                Q(categoria__alocacao='maquina', maquina_destino__fazenda_id=fazenda_id) |
                Q(categoria__alocacao='benfeitoria', benfeitoria_destino__fazenda_id=fazenda_id) |
                Q(categoria__alocacao='pastagem', pastagem_destino__fazenda_id=fazenda_id)
            ).values_list('despesa_id', flat=True)
            print(f"IDs de itens encontrados para fazenda: {list(itens_fazenda)}")
            
            queryset = queryset.filter(id__in=itens_fazenda)
            print(f"Despesas após filtro de fazenda: {queryset.count()}")
            
        # Filtro de fornecedor
        fornecedor_id = self.request.GET.get('fornecedor')
        print(f"Filtro fornecedor_id: {fornecedor_id}")
        if fornecedor_id:
            queryset = queryset.filter(contato_id=fornecedor_id)
            print(f"Despesas após filtro de fornecedor: {queryset.count()}")
            
        # Filtro de status
        status = self.request.GET.get('status')
        print(f"Filtro status: {status}")
        if status:
            if status == 'VENCE_HOJE':
                queryset = queryset.filter(status='PENDENTE', data_vencimento=timezone.localdate())
            elif status == 'VENCIDO':
                queryset = queryset.filter(status='PENDENTE', data_vencimento__lt=timezone.localdate())
            else:
                queryset = queryset.filter(status=status)
            print(f"Despesas após filtro de status: {queryset.count()}")
            
        # Filtro de data
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        print(f"Filtro data_inicio: {data_inicio}, data_fim: {data_fim}")
        
        if data_inicio and data_inicio.strip():
            try:
                queryset = queryset.filter(data_emissao__gte=data_inicio)
                print(f"Despesas após filtro de data início: {queryset.count()}")
            except (ValueError, TypeError) as e:
                print(f"Erro no filtro de data início: {e}")
                
        if data_fim and data_fim.strip():
            try:
                queryset = queryset.filter(data_emissao__lte=data_fim)
                print(f"Despesas após filtro de data fim: {queryset.count()}")
            except (ValueError, TypeError) as e:
                print(f"Erro no filtro de data fim: {e}")
            
        result = queryset.order_by('-data_emissao')
        print(f"Total final de despesas: {result.count()}")
        print("=== DEBUG: Finalizando get_queryset ===\n")
        return result
    
    def get_context_data(self, **kwargs):
        print("\n=== DEBUG: Iniciando get_context_data ===")
        context = super().get_context_data(**kwargs)
        
        # Adiciona fazendas ao contexto
        fazendas = Fazenda.objects.filter(usuario=self.request.user).order_by('nome')
        context['fazendas'] = fazendas
        print(f"Total de fazendas: {fazendas.count()}")
        
        # Adiciona fornecedores ao contexto
        fornecedores = Contato.objects.filter(
            usuario=self.request.user,
            tipo='FO'
        ).order_by('nome')
        context['fornecedores'] = fornecedores
        print(f"Total de fornecedores: {fornecedores.count()}")
        
        # Adiciona filtros atuais ao contexto
        context['filtros'] = {
            'fazenda': self.request.GET.get('fazenda', ''),
            'fornecedor': self.request.GET.get('fornecedor', ''),
            'status': self.request.GET.get('status', ''),
            'data_inicio': self.request.GET.get('data_inicio', ''),
            'data_fim': self.request.GET.get('data_fim', '')
        }
        print(f"Filtros ativos: {context['filtros']}")
        
        # Calcular totais por status
        totais_status = defaultdict(lambda: {'valor': Decimal('0.00'), 'quantidade': 0})
        
        for despesa in self.get_queryset():
            status_real = despesa.status
            if status_real == 'PENDENTE':
                if despesa.data_vencimento == timezone.localdate():
                    status_real = 'VENCE_HOJE'
                elif despesa.data_vencimento < timezone.localdate():
                    status_real = 'VENCIDO'
            
            status_info = totais_status[status_real]
            valor_total = despesa.valor_total()
            status_info['valor'] += valor_total
            status_info['quantidade'] += 1
            print(f"Despesa {despesa.id} - Status: {status_real}, Valor: {valor_total}")
            
        # Formata os valores para exibição
        for status, info in totais_status.items():
            info['valor_formatado'] = '{:,.2f}'.format(info['valor']).replace(',', '.')
            print(f"Total {status}: {info['valor_formatado']} ({info['quantidade']} despesas)")
            
        context['totais_status'] = totais_status
        context['active_tab'] = 'financeiro'
        
        print("=== DEBUG: Finalizando get_context_data ===\n")
        return context
