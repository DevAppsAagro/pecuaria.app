from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import redirect
from django.contrib import messages

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
                login(request, user)
                return True
            except User.DoesNotExist:
                messages.error(request, 'Usuário não encontrado.')
                return False
        else:
            messages.error(request, 'Email ou senha inválidos.')
            return False
            
    except Exception as e:
        messages.error(request, f'Erro ao fazer login: {str(e)}')
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
