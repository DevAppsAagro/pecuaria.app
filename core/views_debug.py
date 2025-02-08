from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from django.db.models import Q
from .models import Despesa, ItemDespesa, Fazenda, Contato

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
