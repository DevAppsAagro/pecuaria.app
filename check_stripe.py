import os
import sys
import django
from django.conf import settings

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pecuaria_project.settings')
django.setup()

import stripe
import logging

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_stripe_config():
    """Verifica a configuração do Stripe"""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    print(f"Verificando a configuração do Stripe usando a chave: {settings.STRIPE_SECRET_KEY[:5]}...")
    
    # Verificar a conexão com o Stripe
    try:
        account = stripe.Account.retrieve()
        print(f"[OK] Conexão com Stripe OK: {account.id}")
        
        # Listar todos os produtos
        print("\n--- Produtos ---")
        products = stripe.Product.list(limit=100)
        if products.data:
            for product in products.data:
                print(f"Produto: {product.name} (ID: {product.id})")
        else:
            print("Nenhum produto encontrado.")
            
        # Listar todos os preços
        print("\n--- Preços ---")
        prices = stripe.Price.list(limit=100)
        if prices.data:
            for price in prices.data:
                amount = price.unit_amount / 100  # Convertendo de centavos para a moeda
                if hasattr(price, 'recurring') and price.recurring:
                    interval = price.recurring.interval
                    print(f"Preço: {price.nickname or price.id} - {amount} {price.currency.upper()}/{interval} (ID: {price.id})")
                else:
                    print(f"Preço: {price.nickname or price.id} - {amount} {price.currency.upper()} (ID: {price.id})")
        else:
            print("Nenhum preço encontrado.")
            
        # Verificar se os IDs nas variáveis de ambiente existem
        print("\n--- Verificação de IDs nos ambientes ---")
        mensal_price_id = settings.STRIPE_MENSAL_PRICE_ID
        anual_price_id = settings.STRIPE_ANUAL_PRICE_ID
        
        mensal_price = None
        anual_price = None
        
        try:
            if mensal_price_id:
                mensal_price = stripe.Price.retrieve(mensal_price_id)
                print(f"[OK] Preço mensal encontrado: {mensal_price_id}")
            else:
                print("[ERRO] ID de preço mensal não configurado no .env")
        except stripe.error.StripeError as e:
            print(f"[ERRO] Erro ao buscar preço mensal: {str(e)}")
        
        try:
            if anual_price_id:
                anual_price = stripe.Price.retrieve(anual_price_id)
                print(f"[OK] Preço anual encontrado: {anual_price_id}")
            else:
                print("[ERRO] ID de preço anual não configurado no .env")
        except stripe.error.StripeError as e:
            print(f"[ERRO] Erro ao buscar preço anual: {str(e)}")
            
        # Verificar webhook
        print("\n--- Webhooks ---")
        webhooks = stripe.WebhookEndpoint.list()
        if webhooks.data:
            for webhook in webhooks.data:
                print(f"Webhook: {webhook.url} (ID: {webhook.id})")
                print(f"  Eventos: {', '.join(webhook.enabled_events)}")
        else:
            print("Nenhum webhook configurado.")
            
        return True
    except stripe.error.StripeError as e:
        print(f"[ERRO] Erro ao conectar com o Stripe: {str(e)}")
        return False
    except Exception as e:
        print(f"[ERRO] Erro desconhecido: {str(e)}")
        return False

if __name__ == "__main__":
    check_stripe_config()
