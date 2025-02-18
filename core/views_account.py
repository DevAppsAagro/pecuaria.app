from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .models import Profile
from supabase import create_client, Client
from django.conf import settings
import uuid
import os

@login_required
def profile_view(request):
    # Garantir que o usuário tem um perfil
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Atualizar informações do perfil
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.email = request.POST.get('email')
            request.user.save()
            
            profile.phone = request.POST.get('phone')
            
            # Processar foto do perfil
            if request.FILES.get('photo'):
                photo_file = request.FILES['photo']
                
                # Criar nome único para o arquivo
                file_ext = os.path.splitext(photo_file.name)[1]
                file_name = f"profile_photos/{uuid.uuid4()}{file_ext}"
                
                try:
                    # Inicializar cliente Supabase
                    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    
                    # Upload do arquivo
                    result = supabase.storage.from_('profile-photos').upload(
                        file_name,
                        photo_file.read(),
                        {"content-type": photo_file.content_type}
                    )
                    
                    # Gerar URL pública
                    public_url = supabase.storage.from_('profile-photos').get_public_url(file_name)
                    
                    # Deletar foto antiga se existir
                    if profile.photo_url:
                        old_file_name = profile.photo_url.split('/')[-1]
                        try:
                            supabase.storage.from_('profile-photos').remove([old_file_name])
                        except:
                            pass
                    
                    profile.photo_url = public_url
                    
                except Exception as e:
                    messages.error(request, f'Erro ao fazer upload da foto: {str(e)}')
            
            profile.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Verificar se as senhas novas coincidem
            if new_password != confirm_password:
                messages.error(request, 'As novas senhas não coincidem!')
                return redirect('profile')
                
            # Verificar se a senha atual está correta
            if not request.user.check_password(current_password):
                messages.error(request, 'A senha atual está incorreta!')
                return redirect('profile')
                
            # Alterar a senha
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Manter o usuário logado
            messages.success(request, 'Sua senha foi alterada com sucesso!')
                    
        return redirect('profile')
        
    return render(request, 'account/profile.html')
