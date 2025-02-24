from django.core.management.base import BaseCommand
import requests
import json
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Envia um evento de teste para o webhook da Eduzz'

    def handle(self, *args, **options):
        # URL do webhook (local)
        webhook_url = 'http://localhost:8000/api/eduzz/webhook/'
        
        # Dados do evento de teste
        payload = {
            'event_type': 'myeduzz.invoice_created',
            'invoice_id': 'TEST123',
            'status': 'paid',
            'customer_email': 'teste@teste.com',
            'customer_name': 'Usuario Teste',
            'product_id': settings.EDUZZ_SOFTWARE_CORTESIA_ID_3F,
            'created_at': datetime.now().isoformat(),
            'test': True  # Indica que é um evento de teste
        }
        
        # Converte para JSON
        json_payload = json.dumps(payload)
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.EDUZZ_ACCESS_TOKEN}'
        }
        
        self.stdout.write('Enviando evento de teste para o webhook...')
        self.stdout.write(f'Payload: {json_payload}')
        
        try:
            # Envia a requisição
            response = requests.post(webhook_url, data=json_payload, headers=headers)
            
            # Exibe o resultado
            self.stdout.write(f'Status code: {response.status_code}')
            self.stdout.write(f'Resposta: {response.text}')
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('Evento de teste enviado com sucesso!'))
            else:
                self.stdout.write(self.style.ERROR('Erro ao enviar evento de teste!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {str(e)}'))
