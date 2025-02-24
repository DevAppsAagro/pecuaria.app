from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.urls import reverse
from .auth_supabase import register_with_email

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        try:
            # Verificar se o usuário já existe
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Este email já está cadastrado.')
                return render(request, 'registration/register.html')
            
            # Registrar usuário usando a função do Supabase
            result = register_with_email(request, email, password, first_name, last_name)
            if result:
                return result  # Retorna o redirect para verificação de email
            
        except Exception as e:
            messages.error(request, f'Erro ao criar conta: {str(e)}')
            
    return render(request, 'registration/register.html')

def redefinir_senha_view(request):
    """
    View para redefinição de senha usando Supabase.
    Recebe o token de redefinição via URL e permite ao usuário definir uma nova senha.
    """
    if request.method == 'GET':
        # Renderiza o template com o formulário de redefinição de senha
        return render(request, 'registration/redefinir_senha.html')
    
    # O processamento do POST é feito diretamente no frontend via Supabase
    # Ver o script em redefinir_senha.html
    return render(request, 'registration/redefinir_senha.html')