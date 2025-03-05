"""
API de integração com o Stripe para gerenciar pagamentos e assinaturas
"""
import logging
import stripe
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# Configure o logger
logger = logging.getLogger(__name__)

class StripeAPI:
    """
    Classe para interagir com a API do Stripe
    """
    
    def __init__(self):
        """
        Inicializa a API do Stripe com a chave da API
        """
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.api_base = settings.STRIPE_API_BASE
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        logger.info(f"StripeAPI inicializada com base URL: {self.api_base}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão com a API do Stripe
        """
        try:
            # Tenta obter os detalhes da conta para verificar a conexão
            account = stripe.Account.retrieve()
            logger.info(f"Conexão com Stripe testada com sucesso: {account.id}")
            return {
                'success': True,
                'data': {
                    'account_id': account.id,
                    'account_name': account.business_profile.get('name', ''),
                    'account_email': account.email
                }
            }
        except Exception as e:
            logger.error(f"Erro ao testar conexão com Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria um novo cliente no Stripe
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Cliente Stripe criado: {customer.id} para {email}")
            return {
                'success': True,
                'customer_id': customer.id,
                'data': customer
            }
        except Exception as e:
            logger.error(f"Erro ao criar cliente no Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Obtém os detalhes de um cliente no Stripe
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                'success': True,
                'data': customer
            }
        except Exception as e:
            logger.error(f"Erro ao obter cliente do Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_customer_by_email(self, email: str) -> Dict[str, Any]:
        """
        Procura um cliente no Stripe pelo e-mail
        """
        try:
            customers = stripe.Customer.list(email=email, limit=1)
            if customers and customers.data:
                return {
                    'success': True,
                    'customer_id': customers.data[0].id,
                    'data': customers.data[0]
                }
            return {
                'success': False,
                'error': 'Cliente não encontrado'
            }
        except Exception as e:
            logger.error(f"Erro ao procurar cliente por e-mail no Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_product(self, name: str, description: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria um novo produto no Stripe
        """
        try:
            product = stripe.Product.create(
                name=name,
                description=description,
                metadata=metadata or {}
            )
            logger.info(f"Produto Stripe criado: {product.id}")
            return {
                'success': True,
                'product_id': product.id,
                'data': product
            }
        except Exception as e:
            logger.error(f"Erro ao criar produto no Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_price(self, product_id: str, unit_amount: int, currency: str = 'brl', 
                     recurring: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria um novo preço para um produto no Stripe
        """
        try:
            price_data = {
                'product': product_id,
                'unit_amount': unit_amount,  # Em centavos (ex: 1990 = R$19,90)
                'currency': currency,
                'metadata': metadata or {}
            }
            
            if recurring:
                price_data['recurring'] = recurring
                
            price = stripe.Price.create(**price_data)
            logger.info(f"Preço Stripe criado: {price.id} para produto {product_id}")
            return {
                'success': True,
                'price_id': price.id,
                'data': price
            }
        except Exception as e:
            logger.error(f"Erro ao criar preço no Stripe: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_checkout_session(self, price_id: str, customer_email: str, 
                               success_url: str, cancel_url: str,
                               mode: str = 'subscription', 
                               metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria uma sessão de checkout para pagamento
        """
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode=mode,  # 'subscription' ou 'payment'
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata or {}
            )
            logger.info(f"Sessão de checkout criada: {checkout_session.id}")
            return {
                'success': True,
                'session_id': checkout_session.id,
                'url': checkout_session.url,
                'data': checkout_session
            }
        except Exception as e:
            logger.error(f"Erro ao criar sessão de checkout: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_subscription(self, customer_id: str, price_id: str, 
                           metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria uma assinatura diretamente (sem checkout)
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                metadata=metadata or {}
            )
            logger.info(f"Assinatura criada: {subscription.id} para cliente {customer_id}")
            return {
                'success': True,
                'subscription_id': subscription.id,
                'data': subscription
            }
        except Exception as e:
            logger.error(f"Erro ao criar assinatura: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de uma assinatura
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'success': True,
                'data': subscription
            }
        except Exception as e:
            logger.error(f"Erro ao obter assinatura {subscription_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancela uma assinatura
        """
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            logger.info(f"Assinatura {subscription_id} cancelada")
            return {
                'success': True,
                'data': subscription
            }
        except Exception as e:
            logger.error(f"Erro ao cancelar assinatura {subscription_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_subscription(self, subscription_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza uma assinatura
        """
        try:
            subscription = stripe.Subscription.modify(subscription_id, **data)
            logger.info(f"Assinatura {subscription_id} atualizada")
            return {
                'success': True,
                'data': subscription
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar assinatura {subscription_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def construct_event(self, payload, signature):
        """
        Construir um evento a partir do payload recebido de um webhook
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Erro de verificação de assinatura: {str(e)}")
            return None
        except ValueError as e:
            logging.error(f"Erro na construção do evento: {str(e)}")
            return None
    
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de uma fatura
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return {
                'success': True,
                'data': invoice
            }
        except Exception as e:
            logger.error(f"Erro ao obter fatura {invoice_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_trial_subscription(self, customer_id: str, price_id: str, 
                                 trial_days: int = 7, 
                                 metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria uma assinatura com período de avaliação
        """
        try:
            trial_end = int((timezone.now() + timedelta(days=trial_days)).timestamp())
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_end=trial_end,
                metadata=metadata or {}
            )
            logger.info(f"Assinatura trial criada: {subscription.id} para cliente {customer_id}")
            return {
                'success': True,
                'subscription_id': subscription.id,
                'data': subscription
            }
        except Exception as e:
            logger.error(f"Erro ao criar assinatura trial: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        """
        Cria uma sessão do portal de clientes do Stripe
        """
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            logger.info(f"Sessão do portal criada para cliente {customer_id}")
            return {
                'success': True,
                'url': portal_session.url,
                'data': portal_session
            }
        except Exception as e:
            logger.error(f"Erro ao criar sessão do portal: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
