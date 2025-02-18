import os
import django
import requests
from decimal import Decimal
from datetime import datetime
import json
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pecuaria_project.settings')
django.setup()

from django.conf import settings
from core.models_eduzz import ClienteLegado

def get_eduzz_customers():
    """Busca todos os clientes da Eduzz"""
    url = "https://api.eduzz.com/myeduzz/v1/customers"
    token = os.getenv('EDUZZ_API_KEY')
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Configurações:")
    print(f"- URL: {url}")
    print(f"- Token: {token[:10]}...")
    print(f"- Headers: {json.dumps(headers, indent=2)}")
    
    # Vamos buscar página por página
    page = 1
    all_customers = []
    
    while True:
        print(f"\nBuscando página {page}...")
        params = {
            "page": page,
            "itemsPerPage": 100  # Máximo permitido
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"- Status: {response.status_code}")
            print(f"- Response Headers: {dict(response.headers)}")
            print(f"- Response Body: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                customers = data.get('items', [])
                all_customers.extend(customers)
                
                print(f"- Encontrados {len(customers)} clientes nesta página")
                
                # Verifica se tem mais páginas
                if page >= data.get('pages', 1):
                    break
                page += 1
            else:
                print(f"Erro ao buscar clientes: {response.status_code}")
                print(f"Resposta: {response.text}")
                break
                
        except Exception as e:
            print(f"Erro ao fazer requisição: {str(e)}")
            break
    
    return all_customers

def get_customer_purchases(customer_id):
    """Busca as compras de um cliente específico"""
    url = f"https://api.eduzz.com/myeduzz/v1/customers/{customer_id}/purchases"
    token = os.getenv('EDUZZ_API_KEY')
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        else:
            print(f"Erro ao buscar compras do cliente {customer_id}: {response.status_code}")
            print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro ao buscar compras do cliente {customer_id}: {str(e)}")
    
    return []

def import_clients():
    """Importa clientes da Eduzz para o banco de dados"""
    print("\nBuscando clientes na Eduzz...")
    customers = get_eduzz_customers()
    print(f"\nTotal de clientes encontrados: {len(customers)}")
    
    clientes_planilha = 0
    
    for customer in customers:
        email = customer.get('email')
        nome = customer.get('name')
        customer_id = customer.get('id')
        
        if not email or not nome:
            continue
            
        # Busca as compras do cliente
        purchases = get_customer_purchases(customer_id)
        
        # Verifica se o cliente comprou a planilha
        comprou_planilha = any(
            str(purchase.get('productId')) == str(settings.EDUZZ_PLANILHA_ID)
            for purchase in purchases
        )
        
        if comprou_planilha:
            # Cria ou atualiza o cliente
            cliente, created = ClienteLegado.objects.get_or_create(
                email=email,
                defaults={
                    'nome': nome,
                    'percentual_desconto': Decimal('100.00'),  # 100% de desconto na adesão
                    'ativo': True,
                    'id_eduzz_antigo': customer_id
                }
            )
            
            if created:
                print(f"Cliente criado: {nome} ({email})")
            else:
                print(f"Cliente já existe: {nome} ({email})")
                
            clientes_planilha += 1
    
    print(f"\nTotal de clientes da planilha importados: {clientes_planilha}")

if __name__ == '__main__':
    print("="*50)
    print("Iniciando importação de clientes da Eduzz...")
    print("="*50)
    import_clients()
    print("\nImportação concluída!")
    print("="*50)
