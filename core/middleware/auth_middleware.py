from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from functools import wraps
from django.contrib import messages

def auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar se o usuário está autenticado via Supabase
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            messages.error(request, 'Você precisa estar logado para acessar esta página.')
            return redirect(reverse('login'))
            
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
