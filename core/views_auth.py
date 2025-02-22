from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

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