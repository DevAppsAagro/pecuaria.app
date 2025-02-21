import requests
from django.conf import settings
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, List, Any
import logging
from django.utils import timezone
from django.db import models
from supabase import create_client, Client
from django.contrib.auth.models import User
from .models_eduzz import UserSubscription, ClientePlanilha, EduzzTransaction
from dateutil import parser

logger = logging.getLogger(__name__)

supabase_url: str = settings.SUPABASE_URL
supabase_key: str = settings.SUPABASE_KEY
supabase: Client = create_client(supabase_url, supabase_key)

class EduzzAPI:
    def __init__(self):
        # Tenta obter das settings, senão usa valores padrão
        self.base_url = settings.EDUZZ_API_URL
        self.api_url = f"{settings.EDUZZ_API_URL}/api/1.1"  # Versão correta da API
        self.api_key = settings.EDUZZ_API_KEY
        self.public_key = settings.EDUZZ_PUBLIC_KEY
        self.origin_key = getattr(settings, 'EDUZZ_ORIGIN_KEY', "0d164417-4a93-4c80-b66a-b9e0f550781b")
        self.access_token = getattr(settings, 'EDUZZ_ACCESS_TOKEN', "edzpap_QNsV8gHLcpO_YypKdhEn2FSf_kB_xndYrfEIMpjg-BAlTtFew8hlEmyPKpWigQvwhbixBSq5vaE759xQo3e")

    def _get_headers(self) -> Dict[str, str]:
        """Retorna os headers com o token de acesso"""
        return {
            'publickey': self.public_key,
            'apikey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _handle_response(self, response: requests.Response, error_message: str) -> Optional[Dict[str, Any]]:
        """Processa a resposta da API e trata erros"""
        try:
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"{error_message}: {str(e)}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        except Exception as e:
            print(f"Erro inesperado: {str(e)}")
            return None

    def _make_request(self, method: str, url: str, json: Dict[str, Any] = None) -> Optional[requests.Response]:
        """Faz uma requisição para a API da Eduzz"""
        try:
            # Adiciona timeout para evitar espera infinita
            response = requests.request(
                method, 
                url, 
                json=json, 
                headers=self._get_headers(),
                timeout=30,  # 30 segundos de timeout
                verify=True  # Verifica certificado SSL
            )
            
            # Log da resposta
            logger.info(f"Request to Eduzz API: {method} {url}")
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text[:500]}")  # Limita o log a 500 caracteres
            
            return response
            
        except requests.exceptions.Timeout:
            logger.error("Timeout ao conectar com a API da Eduzz")
            return None
        except requests.exceptions.SSLError:
            logger.error("Erro de SSL ao conectar com a API da Eduzz")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão com a API da Eduzz: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar com a API da Eduzz: {str(e)}")
            return None

    def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com a API da Eduzz"""
        logger.info("Testando conexão com a API da Eduzz...")
        
        url = f"{self.api_url}/sale/get_sale_list"
        logger.info(f"URL: {url}")
        logger.info(f"Headers: {self._get_headers()}")
        
        response = self._make_request('GET', url)
        
        if not response:
            return {
                'success': False,
                'error': 'Não foi possível conectar com a API da Eduzz.'
            }
        
        if response.status_code == 401:
            return {
                'success': False,
                'error': 'Token de acesso inválido.'
            }
        
        try:
            data = response.json()
        except:
            data = {'message': response.text}
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': 'Conexão estabelecida com sucesso!',
                'data': data
            }
        
        return {
            'success': False,
            'error': f'Erro ao conectar com a Eduzz. Status code: {response.status_code}',
            'response': str(data)
        }

    def get_subscription_status(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Obtém o status da assinatura na Eduzz"""
        url = f"{self.base_url}/subscriptions/v1/{subscription_id}"
        response = requests.get(url, headers=self._get_headers())
        return self._handle_response(response, "Erro ao consultar assinatura na Eduzz")

    def create_subscription(self, user_email: str, plan_id: str) -> Optional[str]:
        """Cria uma nova assinatura na Eduzz"""
        url = f"{self.base_url}/subscriptions/v1"
        data = {
            "email": user_email,
            "plan_id": plan_id
        }
        
        response = requests.post(url, json=data, headers=self._get_headers())
        result = self._handle_response(response, "Erro ao criar assinatura na Eduzz")
        
        if result and result.get('success'):
            return result.get('data', {}).get('subscription_id')
        return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancela uma assinatura na Eduzz"""
        url = f"{self.base_url}/subscriptions/v1/{subscription_id}/cancel"
        response = requests.post(url, headers=self._get_headers())
        result = self._handle_response(response, "Erro ao cancelar assinatura na Eduzz")
        return bool(result and result.get('success'))

    def get_payment_history(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Obtém o histórico de pagamentos de uma assinatura"""
        url = f"{self.base_url}/subscriptions/v1/{subscription_id}/payments"
        response = requests.get(url, headers=self._get_headers())
        result = self._handle_response(response, "Erro ao obter histórico de pagamentos na Eduzz")
        
        if result and result.get('success'):
            return result.get('data', [])
        return []

    def get_plans(self) -> List[Dict[str, Any]]:
        """Obtém a lista de planos disponíveis na Eduzz"""
        url = f"{self.base_url}/subscription/plans"
        response = self._make_request('GET', url)
        return response.json() if response else None

    def create_checkout_url(self, plan_id: str, user_email: str, user_name: str, user_document: str = None) -> Optional[str]:
        """Cria uma URL de checkout para um plano específico"""
        url = f"{self.base_url}/subscription/checkout"
        data = {
            'plan_id': plan_id,
            'customer_email': user_email,
            'customer_name': user_name,
            'customer_document': user_document,
            'return_url': settings.EDUZZ_RETURN_URL,
            'notification_url': settings.EDUZZ_WEBHOOK_URL
        }
        response = self._make_request('POST', url, json=data)
        return response.json().get('checkout_url') if response else None

    def get_subscription_invoices(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Obtém as faturas de uma assinatura"""
        url = f"{self.base_url}/subscriptions/v1/{subscription_id}/invoices"
        response = requests.get(url, headers=self._get_headers())
        result = self._handle_response(response, "Erro ao obter faturas da assinatura na Eduzz")
        
        if result and result.get('success'):
            return result.get('data', [])
        return []

    def update_subscription(self, subscription_id: str, data: Dict[str, Any]) -> bool:
        """Atualiza uma assinatura existente"""
        url = f"{self.base_url}/subscriptions/v1/{subscription_id}"
        response = requests.put(url, json=data, headers=self._get_headers())
        result = self._handle_response(response, "Erro ao atualizar assinatura na Eduzz")
        return bool(result and result.get('success'))

    def get_customer_purchases(self, email):
        """Busca as compras de um cliente pelo email"""
        # Tenta primeiro a API antiga
        url = "https://api-prod.eduzz.com/api/1.1/sale/get_sale_list"
        headers = self._get_headers()
        params = {
            'email': email,
            'status': 3  # 3 = Aprovado
        }
        
        try:
            logger.info(f"Buscando compras do cliente {email} na API antiga...")
            logger.info(f"URL: {url}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    logger.info(f"Compras encontradas na API antiga: {data}")
                    return data.get('data', [])
                    
            # Se não encontrou na API antiga, tenta a nova API
            url = f"{self.base_url}/accounts/v1/customers/search"
            params = {'email': email}
            
            logger.info(f"Buscando compras do cliente {email} na API nova...")
            logger.info(f"URL: {url}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    logger.info(f"Compras encontradas na API nova: {data}")
                    return data.get('data', [])
            
            logger.warning(f"Nenhuma compra encontrada para o cliente {email}")
            return []
            
        except Exception as e:
            logger.error(f"Erro ao buscar compras do cliente {email}: {str(e)}", exc_info=True)
            return []

    def process_webhook(self, data):
        """Processa o webhook da Eduzz"""
        try:
            logger.info("Recebendo webhook da Eduzz:")
            logger.info(f"Dados: {data}")
            
            # Obtém os dados da transação
            transaction_id = data.get('trans_cod')
            product_id = data.get('product_cod')
            status = data.get('trans_status')
            email = data.get('cus_email')
            name = data.get('cus_name')
            phone = data.get('cus_tel')
            customer_id = data.get('cus_cod')
            valor_original = data.get('trans_value', 0)
            valor_pago = data.get('trans_paid', 0)
            data_pagamento = data.get('trans_paid_date')
            
            # Converte status da Eduzz para nosso formato
            status_map = {
                '1': 'pending',    # Pendente
                '3': 'paid',       # Pago
                '4': 'canceled',   # Cancelado
                '6': 'refunded',   # Reembolsado
                '7': 'pending',    # Aguardando reembolso
            }
            
            # Registra a transação
            EduzzTransaction.objects.update_or_create(
                transaction_id=transaction_id,
                defaults={
                    'email': email,
                    'nome': name,
                    'status': status_map.get(status, 'pending'),
                    'product_id': product_id,
                    'valor_original': valor_original,
                    'valor_pago': valor_pago,
                    'data_pagamento': parser.parse(data_pagamento) if data_pagamento else None,
                    'webhook_data': data
                }
            )
            
            logger.info(f"Transação {transaction_id} registrada com sucesso")
            
            if status == '3':  # 3 = Aprovado
                # Verifica se é uma compra da planilha
                if str(product_id) == settings.EDUZZ_PLANILHA_ID:
                    # Registra no Supabase
                    supabase.table('clienteplanilha').upsert({
                        'email': email,
                        'nome': name,
                        'telefone': phone,
                        'eduzz_customer_id': customer_id,
                        'data_compra': timezone.now().isoformat()
                    }).execute()
                    
                    # Registra também no Django
                    ClientePlanilha.objects.get_or_create(
                        email=email,
                        defaults={
                            'nome': name,
                            'telefone': phone,
                            'eduzz_customer_id': customer_id
                        }
                    )
                    logger.info(f"Cliente {email} registrado como cliente da planilha")
                    return True
                
                # Se não for uma compra da planilha, verifica se é uma assinatura
                if str(product_id) in [
                    settings.EDUZZ_SOFTWARE_MENSAL_ID_3F,
                    settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID_3F,
                    settings.EDUZZ_SOFTWARE_ANUAL_ID_3F,
                    settings.EDUZZ_SOFTWARE_ANUAL_SEM_ADESAO_ID_3F,
                    settings.EDUZZ_SOFTWARE_CORTESIA_ID_3F
                ]:
                    # Define o tipo de plano
                    if str(product_id) in [settings.EDUZZ_SOFTWARE_MENSAL_ID_3F, settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID_3F]:
                        plan_type = 'mensal'
                    else:
                        plan_type = 'anual'
                    
                    # Registra no Supabase
                    supabase.table('assinaturas_pendentes').upsert({
                        'email': email,
                        'nome': name,
                        'telefone': phone,
                        'eduzz_customer_id': customer_id,
                        'eduzz_subscription_id': transaction_id,
                        'plan_type': plan_type,
                        'status': 'active',
                        'start_date': timezone.now().isoformat(),
                        'end_date': (timezone.now() + timedelta(days=365 if plan_type == 'anual' else 30)).isoformat(),
                        'last_payment_date': timezone.now().isoformat(),
                        'next_payment_date': (timezone.now() + timedelta(days=365 if plan_type == 'anual' else 30)).isoformat(),
                        'is_legacy': str(product_id) in [
                            settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID_3F,
                            settings.EDUZZ_SOFTWARE_ANUAL_SEM_ADESAO_ID_3F
                        ]
                    }).execute()
                    
                    # Tenta atualizar o usuário se ele já existir
                    try:
                        user = User.objects.get(email=email)
                        UserSubscription.objects.update_or_create(
                            user=user,
                            defaults={
                                'eduzz_subscription_id': transaction_id,
                                'plan_type': plan_type,
                                'status': 'active',
                                'start_date': timezone.now(),
                                'end_date': timezone.now() + timedelta(days=365 if plan_type == 'anual' else 30),
                                'last_payment_date': timezone.now(),
                                'next_payment_date': timezone.now() + timedelta(days=365 if plan_type == 'anual' else 30),
                                'is_legacy': str(product_id) in [
                                    settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID_3F,
                                    settings.EDUZZ_SOFTWARE_ANUAL_SEM_ADESAO_ID_3F
                                ]
                            }
                        )
                        logger.info(f"Assinatura do usuário {email} atualizada com sucesso")
                    except User.DoesNotExist:
                        logger.info(f"Usuário {email} ainda não existe, assinatura será vinculada no registro")
                    
                    return True
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}", exc_info=True)
            return False

    def get_all_sales(self) -> List[Dict[str, Any]]:
        """Obtém todas as vendas da Eduzz"""
        url = f"{self.api_url}/subscription/sales"
        response = self._make_request('GET', url)
        
        if not response:
            return []
            
        try:
            data = response.json()
            sales = []
            
            for sale in data.get('data', []):
                sale_data = {
                    'email': sale.get('customer', {}).get('email'),
                    'plan_id': sale.get('plan_id'),
                    'status': sale.get('status'),
                    'next_billing_date': sale.get('next_billing_date'),
                    'subscription_id': sale.get('subscription_id'),
                    'plan_type': sale.get('plan', {}).get('type'),
                    'start_date': sale.get('start_date'),
                    'end_date': sale.get('end_date'),
                    'last_payment_date': sale.get('last_payment_date')
                }
                sales.append(sale_data)
                
            return sales
        except Exception as e:
            logger.error(f"Erro ao processar vendas da Eduzz: {str(e)}")
            return []
