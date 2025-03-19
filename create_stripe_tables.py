"""
Script para criar migrações e aplicar para modelos StripeCustomer
"""
import os
import sys
import django

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pecuaria.settings')
django.setup()

# Agora podemos importar as models
from django.db import connection

def create_tables():
    """
    Cria as tabelas para os modelos Stripe
    """
    with connection.cursor() as cursor:
        # Verificar se a tabela já existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'core_stripecustomer'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("Criando tabela core_stripecustomer...")
            cursor.execute("""
                CREATE TABLE core_stripecustomer (
                    id SERIAL PRIMARY KEY,
                    stripe_customer_id VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)
            print("Tabela core_stripecustomer criada com sucesso!")
        else:
            print("Tabela core_stripecustomer já existe!")
            
if __name__ == "__main__":
    create_tables()
    print("Processo finalizado!")
