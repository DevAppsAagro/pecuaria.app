from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Despesa, ParcelaDespesa

class Command(BaseCommand):
    help = 'Atualiza o status de despesas e parcelas vencidas ou que vencem hoje'

    def handle(self, *args, **kwargs):
        hoje = timezone.now().date()
        
        # Atualiza despesas
        despesas_vencidas = Despesa.objects.filter(status='PENDENTE', data_vencimento__lt=hoje)
        num_despesas_vencidas = despesas_vencidas.update(status='VENCIDO')
        
        despesas_hoje = Despesa.objects.filter(status='PENDENTE', data_vencimento=hoje)
        num_despesas_hoje = despesas_hoje.update(status='VENCE_HOJE')
        
        # Atualiza parcelas
        parcelas_vencidas = ParcelaDespesa.objects.filter(status='PENDENTE', data_vencimento__lt=hoje)
        num_parcelas_vencidas = parcelas_vencidas.update(status='VENCIDO')
        
        parcelas_hoje = ParcelaDespesa.objects.filter(status='PENDENTE', data_vencimento=hoje)
        num_parcelas_hoje = parcelas_hoje.update(status='VENCE_HOJE')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Atualizado status:\n'
                f'- {num_despesas_vencidas} despesas para VENCIDO\n'
                f'- {num_despesas_hoje} despesas para VENCE HOJE\n'
                f'- {num_parcelas_vencidas} parcelas para VENCIDO\n'
                f'- {num_parcelas_hoje} parcelas para VENCE HOJE'
            )
        )
