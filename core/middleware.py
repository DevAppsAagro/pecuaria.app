from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404
from .models import Fazenda

class FazendaAtualMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # Tenta pegar a fazenda_id da sessão
            fazenda_id = request.session.get('fazenda_atual_id')
            
            if fazenda_id:
                # Se tem fazenda_id na sessão, busca a fazenda
                try:
                    fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
                    request.user.fazenda_atual = fazenda
                except Fazenda.DoesNotExist:
                    # Se a fazenda não existe mais, remove da sessão
                    del request.session['fazenda_atual_id']
                    request.user.fazenda_atual = None
            else:
                # Se não tem fazenda na sessão, pega a primeira do usuário
                fazenda = Fazenda.objects.filter(usuario=request.user).first()
                if fazenda:
                    request.session['fazenda_atual_id'] = fazenda.id
                    request.user.fazenda_atual = fazenda
                else:
                    request.user.fazenda_atual = None
