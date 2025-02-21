from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import redirect
from django.contrib import messages
from .models_eduzz import UserSubscription, ClientePlanilha

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def register_with_email(request, email, password, first_name='', last_name=''):
    try:
        # Registrar usuário no Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Criar usuário no Django
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Verifica se o usuário tem uma assinatura pendente
            assinatura = supabase.table('assinaturas_pendentes').select('*').eq('email', email).execute()
            if assinatura.data:
                assinatura = assinatura.data[0]
                UserSubscription.objects.create(
                    user=user,
                    eduzz_subscription_id=assinatura['eduzz_subscription_id'],
                    plan_type=assinatura['plan_type'],
                    status=assinatura['status'],
                    start_date=assinatura['start_date'],
                    end_date=assinatura['end_date'],
                    last_payment_date=assinatura['last_payment_date'],
                    next_payment_date=assinatura['next_payment_date'],
                    is_legacy=assinatura['is_legacy']
                )
                # Remove a assinatura pendente
                supabase.table('assinaturas_pendentes').delete().eq('email', email).execute()
            
            # Verifica se o usuário comprou a planilha
            planilha = supabase.table('clienteplanilha').select('*').eq('email', email).execute()
            if planilha.data:
                planilha = planilha.data[0]
                ClientePlanilha.objects.create(
                    email=email,
                    nome=planilha['nome'],
                    telefone=planilha.get('telefone'),
                    eduzz_customer_id=planilha['eduzz_customer_id']
                )
                # Remove o registro da planilha
                supabase.table('clienteplanilha').delete().eq('email', email).execute()
            
            messages.success(request, 'Conta criada com sucesso! Verifique seu email para confirmar seu cadastro.')
            return redirect('verificar_email')
        else:
            messages.error(request, 'Erro ao criar conta. Tente novamente.')
            return False
            
    except Exception as e:
        error_message = str(e)
        if "For security purposes" in error_message:
            messages.error(request, 'Por favor, aguarde alguns segundos antes de tentar novamente.')
        else:
            messages.error(request, f'Erro ao criar conta: {error_message}')
        return False

def login_with_email(request, email, password):
    try:
        # Login no Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Verificar se o email foi confirmado
            if not response.user.email_confirmed_at:
                messages.error(request, 'Por favor, confirme seu email antes de fazer login.')
                return False
                
            # Login no Django
            try:
                user = User.objects.get(email=email)
                
                try:
                    # Verifica se o usuário tem uma assinatura pendente
                    assinatura = supabase.table('assinaturas_pendentes').select('*').eq('email', email).execute()
                    if assinatura.data:
                        assinatura = assinatura.data[0]
                        UserSubscription.objects.update_or_create(
                            user=user,
                            defaults={
                                'eduzz_subscription_id': assinatura['eduzz_subscription_id'],
                                'plan_type': assinatura['plan_type'],
                                'status': assinatura['status'],
                                'start_date': assinatura['start_date'],
                                'end_date': assinatura['end_date'],
                                'last_payment_date': assinatura['last_payment_date'],
                                'next_payment_date': assinatura['next_payment_date'],
                                'is_legacy': assinatura['is_legacy']
                            }
                        )
                        # Remove a assinatura pendente
                        supabase.table('assinaturas_pendentes').delete().eq('email', email).execute()
                except Exception as e:
                    # Se houver erro ao acessar assinaturas_pendentes, apenas loga o erro e continua
                    print(f"Erro ao verificar assinaturas pendentes: {str(e)}")
                
                try:
                    # Verifica se o usuário comprou a planilha
                    planilha = supabase.table('clienteplanilha').select('*').eq('email', email).execute()
                    if planilha.data:
                        planilha = planilha.data[0]
                        ClientePlanilha.objects.update_or_create(
                            email=email,
                            defaults={
                                'nome': planilha['nome'],
                                'telefone': planilha.get('telefone'),
                                'eduzz_customer_id': planilha['eduzz_customer_id']
                            }
                        )
                        # Remove o registro da planilha
                        supabase.table('clienteplanilha').delete().eq('email', email).execute()
                except Exception as e:
                    # Se houver erro ao acessar clienteplanilha, apenas loga o erro e continua
                    print(f"Erro ao verificar cliente planilha: {str(e)}")
                
                login(request, user)
                return True
                
            except User.DoesNotExist:
                messages.error(request, 'Usuário não encontrado.')
                return False
        else:
            messages.error(request, 'Email ou senha inválidos.')
            return False
            
    except Exception as e:
        error_message = str(e)
        if "Invalid login credentials" in error_message:
            messages.error(request, 'Email ou senha inválidos.')
        else:
            messages.error(request, f'Erro ao fazer login: {error_message}')
        return False

def reset_password(email):
    try:
        supabase.auth.reset_password_email(email)
        return True
    except Exception as e:
        return False

def verify_email(token):
    try:
        response = supabase.auth.verify_email(token)
        return True if response else False
    except Exception as e:
        return False
