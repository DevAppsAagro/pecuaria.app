from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from functools import wraps
from django.contrib import messages

def auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar se o usuário está autenticado via Supabase
        supabase_access_token = request.session.get('supabase_access_token')
        
        if not supabase_access_token:
            messages.error(request, 'Você precisa estar logado para acessar esta página.')
            return redirect(reverse('login'))
            
        # Adiciona o token ao header da requisição
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {supabase_access_token}'
            
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
