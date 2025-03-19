from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django.contrib import messages
# Removido: from .models_eduzz import UserSubscription, ClientePlanilha
from django.http import JsonResponse
import json

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def register_with_email(request, email, password, first_name='', last_name='', phone=''):
    try:
        # Registrar no Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "email_verified": False
                }
            }
        })
        
        if not response or not hasattr(response, 'user') or not response.user:
            print("[DEBUG] Erro: Resposta inválida do Supabase")
            print("[DEBUG] Response:", response)
            messages.error(request, 'Erro ao criar conta. Por favor, tente novamente.')
            return False
            
        # Criar usuário Django
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Adicionar telefone ao perfil do usuário
            profile = user.profile
            profile.telefone = phone
            profile.save()
            
            messages.success(request, 'Conta criada com sucesso! Por favor, verifique seu email para confirmar o cadastro.')
            return True
            
        except Exception as e:
            print(f"[DEBUG] Erro ao criar usuário Django: {str(e)}")
            messages.error(request, 'Erro ao criar conta. Por favor, tente novamente.')
            return False
            
    except Exception as e:
        print(f"[DEBUG] Erro no processo de registro: {str(e)}")
        error_message = str(e)
        if "User already registered" in error_message:
            messages.error(request, 'Este email já está registrado.')
        else:
            messages.error(request, f'Erro ao criar conta: {error_message}')
        return False

def login_with_email(request, email, password, session=None):
    try:
        if password:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        else:
            # Extrair o token de acesso do objeto de sessão
            access_token = session.get('access_token') if isinstance(session, dict) else None
            if not access_token:
                print("[DEBUG] Token de acesso não encontrado na sessão")
                return False
            
            # Usar o token de acesso para obter os dados do usuário
            response = supabase.auth.get_user(access_token)
        
        if not password:  # Login com sessão (token)
            user_data = response.user
            if not user_data:
                print("[DEBUG] Sessão inválida ou expirada")
                return False
            print("[DEBUG] Autenticação com token bem-sucedida")
        else:
            if response.user:
                user_data = response.user
                print("[DEBUG] Autenticação com Supabase bem-sucedida")
            else:
                print("[DEBUG] Erro de autenticação com Supabase")
                return False
        
        # Verificar se o email foi confirmado
        email_confirmed = user_data.email_confirmed_at is not None
        if not email_confirmed and settings.DEBUG:
            print("[DEBUG] Email não confirmado, mas permitindo login em ambiente de desenvolvimento")
        elif not email_confirmed:
            print("[DEBUG] Email não confirmado")
            messages.error(request, 'Por favor, confirme seu email antes de fazer login.')
            return False
        
        # Verificar se usuário existe no Django e criar se não existir
        try:
            user = User.objects.get(email=email)
            print("[DEBUG] Usuário encontrado no Django")
        except User.DoesNotExist:
            print("[DEBUG] Criando novo usuário no Django")
            # Pegar dados do user_metadata
            metadata = user_data.user_metadata
            first_name = metadata.get('first_name', '')
            last_name = metadata.get('last_name', '')
            phone = metadata.get('phone', '')  # Pega o telefone do metadata
            
            # Criar usuário Django
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Criar perfil do usuário se não existir
            from django.db import transaction
            from core.models import Profile
            
            with transaction.atomic():
                try:
                    profile = user.profile
                except Profile.DoesNotExist:
                    profile = Profile.objects.create(user=user)
                
                profile.phone = phone
                profile.save()
            
            print("[DEBUG] Usuário e perfil criados com sucesso")
        
        # Fazer login do usuário no Django
        auth_user = authenticate(username=email, password=password) if password else user
        if auth_user:
            login(request, auth_user)
            print("[DEBUG] Login com Django realizado com sucesso")
            
            # Verificar se o usuário já tem StripeCustomer (simulação)
            try:
                # Tente acessar o cliente Stripe, mas não falhe se o modelo não existir
                try:
                    from .models_stripe import StripeCustomer
                    StripeCustomer.objects.filter(user=user).first()
                except (ImportError, Exception) as e:
                    print(f"[DEBUG] Modelo StripeCustomer não disponível: {str(e)}")
                    pass
                
                return True
            except Exception as e:
                print(f"[DEBUG] Erro no processo de login: {str(e)}")
                return False
        else:
            print("[DEBUG] Falha ao fazer login com Django")
            return False
    
    except Exception as e:
        print(f"[DEBUG] Erro no processo de login: {str(e)}")
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

def update_password(request, new_password):
    """Atualiza a senha do usuário no Supabase"""
    try:
        response = supabase.auth.update_user({
            "password": new_password
        })
        
        if response.user:
            messages.success(request, 'Senha atualizada com sucesso!')
            return True
        else:
            messages.error(request, 'Erro ao atualizar senha.')
            return False
            
    except Exception as e:
        messages.error(request, f'Erro ao atualizar senha: {str(e)}')
        return False

def password_reset_confirm_view(request, token):
    """View para processar o token de redefinição de senha"""
    try:
        # Verificar se o token é válido
        response = supabase.auth.verify_otp({
            "token": token,
            "type": "recovery"
        })
        
        if response.user:
            # Token válido, mostrar formulário de nova senha
            return render(request, 'registration/new_password.html', {
                'token': token,
                'email': response.user.email
            })
        else:
            messages.error(request, 'Link de redefinição de senha inválido ou expirado.')
            return redirect('login')
            
    except Exception as e:
        messages.error(request, 'Erro ao verificar o token de redefinição de senha.')
        return redirect('login')

def update_password_view(request):
    """View para atualizar a senha do usuário via API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
        
    try:
        data = json.loads(request.body)
        new_password = data.get('password')
        
        if not new_password:
            return JsonResponse({'success': False, 'message': 'Senha não fornecida'}, status=400)
            
        # Atualizar senha no Supabase
        response = supabase.auth.update_user({
            "password": new_password
        })
        
        if response.user:
            messages.success(request, 'Senha atualizada com sucesso!')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Erro ao atualizar senha'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})