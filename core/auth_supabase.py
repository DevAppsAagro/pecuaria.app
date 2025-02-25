from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.contrib import messages
from .models_eduzz import UserSubscription, ClientePlanilha
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
        print("\n[DEBUG] Iniciando processo de login...")
        print(f"[DEBUG] Tentando login para o email: {email}")
        
        if session:
            # Usar a sessão fornecida
            print("[DEBUG] Usando sessão fornecida")
            print("[DEBUG] Sessão:", session)
            
            # Configurar tokens
            request.session['supabase_access_token'] = session.get('access_token')
            request.session['supabase_refresh_token'] = session.get('refresh_token')
            request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
            print("[DEBUG] Tokens configurados com sucesso")
            
            # Obter dados do usuário
            try:
                user_response = supabase.auth.get_user(session.get('access_token'))
                print("[DEBUG] Resposta get_user:", user_response)
                
                if not user_response or not user_response.user:
                    print("[DEBUG] Erro: Não foi possível obter dados do usuário")
                    messages.error(request, 'Erro ao obter dados do usuário.')
                    return False
                    
                user_data = user_response.user
                
                # Verificar se o email foi confirmado
                if not user_data.email_confirmed_at:
                    messages.error(request, 'Por favor, confirme seu email antes de fazer login.')
                    return False
                    
                # Login ou criação no Django
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
                        
                        profile.telefone = phone
                        profile.save()
                    
                    print("[DEBUG] Usuário e perfil criados com sucesso")
                    
                login(request, user)
                print("[DEBUG] Login no Django realizado com sucesso")
                return True
                    
            except Exception as e:
                print(f"[DEBUG] Erro ao obter dados do usuário: {str(e)}")
                messages.error(request, 'Erro ao obter dados do usuário.')
                return False
                
        else:
            # Login no Supabase
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            print("[DEBUG] Resposta do Supabase:", response)
            
            if not response or not hasattr(response, 'user') or not response.user:
                print("[DEBUG] Erro: Resposta inválida do Supabase")
                print("[DEBUG] Response:", response)
                print("[DEBUG] Tem atributo user?", hasattr(response, 'user'))
                if hasattr(response, 'user'):
                    print("[DEBUG] User:", response.user)
                messages.error(request, 'Credenciais inválidas. Por favor, verifique seu email e senha.')
                return False
                
            # Armazena o token de acesso na sessão
            print("[DEBUG] Verificando sessão...")
            if hasattr(response, 'session') and response.session:
                print("[DEBUG] Sessão encontrada, configurando tokens...")
                request.session['supabase_access_token'] = response.session.access_token
                request.session['supabase_refresh_token'] = response.session.refresh_token
                request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
                print("[DEBUG] Tokens configurados com sucesso")
            else:
                print("[DEBUG] Erro: Sessão não encontrada")
                print("[DEBUG] Response session:", getattr(response, 'session', None))
                messages.error(request, 'Erro ao processar autenticação. Por favor, tente novamente.')
                return False
            
            user_data = response.user
            
            # Verificar se o email foi confirmado
            if not user_data.email_confirmed_at:
                messages.error(request, 'Por favor, confirme seu email antes de fazer login.')
                return False
                
            # Login ou criação no Django
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
                    
                    profile.telefone = phone
                    profile.save()
                
                print("[DEBUG] Usuário e perfil criados com sucesso")
                
            login(request, user)
            print("[DEBUG] Login no Django realizado com sucesso")
            return True
                
    except Exception as e:
        print(f"[DEBUG] Erro no processo de login: {str(e)}")
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