import requests
from django.conf import settings
from decimal import Decimal
from datetime import datetime
import logging
import json
from .models_eduzz import EduzzTransaction, ClienteLegado

# Configurar logging mais detalhado
logger = logging.getLogger(__name__)

class EduzzAPI:
    def __init__(self):
        self.public_key = settings.EDUZZ_PUBLIC_KEY
        self.api_key = settings.EDUZZ_API_KEY
        self.base_url = "https://api.eduzz.com"
        
        # Log das configurações
        logger.info('='*50)
        logger.info('Inicializando EduzzAPI')
        logger.info('Base URL: %s', self.base_url)
        logger.info('Public Key: %s', self.public_key[:5] + '...' if self.public_key else 'Não configurada')
        logger.info('API Key: %s', self.api_key[:5] + '...' if self.api_key else 'Não configurada')
        logger.info('='*50)

    def create_transaction(self, email, nome, produto_id, valor, tipo_produto):
        """Cria uma nova transação na Eduzz"""
        try:
            logger.info('='*50)
            logger.info('INICIANDO CRIAÇÃO DE TRANSAÇÃO')
            logger.info('='*50)
            
            # Verifica se é cliente legado para aplicar desconto
            cliente = ClienteLegado.objects.filter(email=email, ativo=True).first()
            
            # Log dos dados do cliente
            logger.info('DADOS DO CLIENTE:')
            logger.info('- Email: %s', email)
            logger.info('- Nome: %s', nome)
            logger.info('- Cliente legado: %s', 'Sim' if cliente else 'Não')
            if cliente:
                logger.info('- Detalhes do cliente legado:')
                logger.info('  * ID: %s', cliente.id)
                logger.info('  * Data cadastro: %s', cliente.data_cadastro)
                logger.info('  * Ativo: %s', cliente.ativo)

            # Log dos dados do produto
            logger.info('DADOS DO PRODUTO:')
            logger.info('- ID: %s', produto_id)
            logger.info('- Tipo: %s', tipo_produto)
            logger.info('- Valor: R$ %.2f', float(valor))

            # Prepara os dados para a API da Eduzz
            payload = {
                "items": [{
                    "product_id": produto_id,
                    "amount": float(valor),
                    "quantity": 1
                }],
                "customer": {
                    "email": email,
                    "name": nome
                }
            }

            # Se for cliente legado, adiciona flag para desconto na adesão
            if cliente:
                payload["subscription"] = {
                    "adhesion_free": True
                }
                logger.info('DESCONTO APLICADO: Cliente legado - adesão gratuita')

            # Log do payload
            logger.info('PAYLOAD PARA EDUZZ:')
            logger.info(json.dumps(payload, indent=2))

            # Log dos headers
            headers = {
                "public_key": self.public_key,
                "api_key": self.api_key,
                "Content-Type": "application/json"
            }
            logger.info('HEADERS:')
            logger.info('- Content-Type: application/json')
            logger.info('- Public Key: %s...', headers['public_key'][:5])
            logger.info('- API Key: %s...', headers['api_key'][:5])

            # Faz a requisição para a API da Eduzz
            logger.info('ENVIANDO REQUISIÇÃO...')
            response = requests.post(
                f"{self.base_url}/checkout/create",
                json=payload,
                headers=headers
            )
            
            # Log da resposta
            logger.info('RESPOSTA DA EDUZZ:')
            logger.info('- Status code: %s', response.status_code)
            logger.info('- Headers: %s', dict(response.headers))
            logger.info('- Content: %s', response.text)
            
            if response.status_code == 200:
                data = response.json()
                logger.info('TRANSAÇÃO CRIADA COM SUCESSO:')
                logger.info('- Invoice ID: %s', data.get('invoice_id'))
                logger.info('- Checkout URL: %s', data.get('checkout_url'))
                
                # Determina o plano baseado no produto_id
                plano = 'mensal'
                if produto_id == settings.EDUZZ_SOFTWARE_ANUAL_ID:
                    plano = 'anual'
                elif produto_id == settings.EDUZZ_SOFTWARE_CORTESIA_ID:
                    plano = 'cortesia'
                
                # Cria o registro da transação
                transaction = EduzzTransaction.objects.create(
                    transaction_id=data['invoice_id'],
                    email=email,
                    nome=nome,
                    status='pending',
                    product_id=produto_id,
                    plano=plano,
                    valor_original=Decimal(str(valor)),
                    valor_pago=Decimal('0.00'),
                    is_legado=True if cliente else False,
                    cliente_legado=cliente
                )
                
                logger.info('TRANSAÇÃO SALVA NO BANCO:')
                logger.info('- ID: %s', transaction.id)
                logger.info('- Status: %s', transaction.status)
                logger.info('='*50)
                
                return {
                    'success': True,
                    'checkout_url': data['checkout_url'],
                    'transaction': transaction
                }
            
            error_msg = response.json().get('message', 'Erro ao criar transação')
            logger.error('ERRO NA API DA EDUZZ:')
            logger.error('- Mensagem: %s', error_msg)
            logger.error('='*50)
            return {
                'success': False,
                'error': error_msg
            }
            
        except Exception as e:
            logger.exception('ERRO INESPERADO:')
            logger.error('- Tipo: %s', type(e).__name__)
            logger.error('- Mensagem: %s', str(e))
            logger.error('='*50)
            return {
                'success': False,
                'error': str(e)
            }

    def process_webhook(self, data):
        """Processa webhooks recebidos da Eduzz"""
        try:
            logger.info('='*50)
            logger.info('PROCESSANDO WEBHOOK')
            logger.info('='*50)
            
            # Log dos dados recebidos
            logger.info('DADOS RECEBIDOS:')
            logger.info(json.dumps(data, indent=2))
            
            transaction = EduzzTransaction.objects.filter(
                transaction_id=data['invoice_id']
            ).first()

            if not transaction:
                logger.error('TRANSAÇÃO NÃO ENCONTRADA:')
                logger.error('- Invoice ID: %s', data['invoice_id'])
                logger.error('='*50)
                return False

            # Log do status anterior
            logger.info('STATUS ANTERIOR: %s', transaction.status)

            # Atualiza o status da transação
            transaction.status = data['status']
            
            if data['status'] == 'paid':
                transaction.data_pagamento = datetime.now()
                transaction.valor_pago = Decimal(str(data.get('amount', '0')))
                logger.info('PAGAMENTO CONFIRMADO:')
                logger.info('- Valor pago: R$ %.2f', float(transaction.valor_pago))
                logger.info('- Data: %s', transaction.data_pagamento)

            transaction.save()
            
            logger.info('WEBHOOK PROCESSADO COM SUCESSO')
            logger.info('- Novo status: %s', transaction.status)
            logger.info('='*50)
            return True
            
        except Exception as e:
            logger.exception('ERRO AO PROCESSAR WEBHOOK:')
            logger.error('- Tipo: %s', type(e).__name__)
            logger.error('- Mensagem: %s', str(e))
            logger.error('='*50)
            return False

    def get_transaction_status(self, transaction_id):
        """Consulta o status de uma transação específica"""
        response = requests.get(
            f"{self.base_url}/invoice/{transaction_id}",
            headers={
                "public_key": self.public_key,
                "api_key": self.api_key
            }
        )
        
        if response.status_code == 200:
            return response.json()
        return None
