from django.core.management.base import BaseCommand
from core.eduzz_api import EduzzAPI
from django.conf import settings

class Command(BaseCommand):
    help = 'Busca todos os clientes da planilha na Eduzz'

    def handle(self, *args, **options):
        eduzz = EduzzAPI()
        
        # Testa a conexão com a API
        self.stdout.write('Testando conexão com a API da Eduzz...')
        test = eduzz.test_connection()
        if not test['success']:
            self.stdout.write(self.style.ERROR(f'Erro ao conectar com a Eduzz: {test["error"]}'))
            return
            
        self.stdout.write(self.style.SUCCESS('Conexão estabelecida com sucesso!'))
        
        # Busca as compras
        self.stdout.write('\nBuscando compras da planilha...')
        purchases = eduzz.get_customer_purchases('leonardofelipess@gmail.com')
        
        if not purchases:
            self.stdout.write(self.style.ERROR('Nenhuma compra encontrada'))
            return
            
        planilha_purchases = [
            purchase for purchase in purchases 
            if str(purchase.get('product_id')) == settings.EDUZZ_PLANILHA_ID
        ]
        
        self.stdout.write(self.style.SUCCESS(f'\nEncontradas {len(planilha_purchases)} compras da planilha'))
        
        for purchase in planilha_purchases:
            email = purchase.get('customer_email', 'N/A')
            name = purchase.get('customer_name', 'N/A')
            status = purchase.get('status', 'desconhecido')
            valor = purchase.get('value', 0)
            data = purchase.get('date', 'desconhecida')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCliente encontrado:\n'
                    f'  Nome: {name}\n'
                    f'  Email: {email}\n'
                    f'  Status: {status}\n'
                    f'  Valor: R$ {valor}\n'
                    f'  Data: {data}'
                )
            )
