from django.core.management.base import BaseCommand
from core.models_eduzz import EduzzTransaction
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Mostra os últimos logs de transações da Eduzz'

    def handle(self, *args, **options):
        # Busca transações das últimas 24 horas
        since = timezone.now() - timedelta(hours=24)
        transactions = EduzzTransaction.objects.filter(
            created_at__gte=since
        ).order_by('-created_at')
        
        if not transactions:
            self.stdout.write('Nenhuma transação encontrada nas últimas 24 horas.')
            return
            
        self.stdout.write(self.style.SUCCESS(f'Encontradas {transactions.count()} transações:'))
        self.stdout.write('='*50)
        
        for tx in transactions:
            self.stdout.write(f'ID: {tx.transaction_code}')
            self.stdout.write(f'Status: {tx.status}')
            self.stdout.write(f'Cliente: {tx.customer_name} ({tx.customer_email})')
            self.stdout.write(f'Produto: {tx.product_id}')
            self.stdout.write(f'Data: {tx.created_at}')
            self.stdout.write('-'*50)
