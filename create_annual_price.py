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

def create_annual_price():
    """Cria um plano anual no Stripe"""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        # Verificar se já existe um produto para o plano anual
        products = stripe.Product.list(limit=100)
        annual_product = None
        
        for product in products.data:
            if "anual" in product.name.lower() or "annual" in product.name.lower():
                annual_product = product
                print(f"[OK] Produto anual encontrado: {product.name} (ID: {product.id})")
                break
        
        if not annual_product:
            # Criar um novo produto para o plano anual
            annual_product = stripe.Product.create(
                name="PecuaristaPRO - Anual",
                description="Plano anual do PecuaristaPRO com desconto",
                active=True,
                metadata={
                    "type": "subscription",
                    "period": "annual"
                }
            )
            print(f"[OK] Novo produto anual criado: {annual_product.name} (ID: {annual_product.id})")
        
        # Criar o preço anual
        annual_price = stripe.Price.create(
            product=annual_product.id,
            nickname="Plano Anual",
            unit_amount=4788,  # R$ 47,88 (com desconto em relação ao mensal)
            currency="brl",
            recurring={
                "interval": "year",
                "interval_count": 1
            },
            metadata={
                "type": "subscription",
                "period": "annual"
            }
        )
        
        print(f"[OK] Preço anual criado: {annual_price.id} - R$ {annual_price.unit_amount/100}/ano")
        print("\nAdicione a seguinte linha ao seu arquivo .env:")
        print(f"STRIPE_ANUAL_PRICE_ID={annual_price.id}")
        
        return annual_price.id
    
    except Exception as e:
        print(f"[ERRO] Falha ao criar preço anual: {str(e)}")
        return None

if __name__ == "__main__":
    create_annual_price()
