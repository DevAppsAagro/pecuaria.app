from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
from .models import Fazenda
from .models_eduzz import UserSubscription
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages
from .eduzz_api import EduzzAPI
from django.utils import timezone

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

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lista de URLs que não precisam de verificação
        exempt_urls = [
            'assinatura',
            'planos',
            'login',
            'logout',
            'profile',
            'alterar_plano',
            'webhook_eduzz',
            'verificar_email',
            'static',
            'media',
            'admin',
            'api',
        ]
        
        # Verifica se a URL atual está na lista de exceções
        current_url = request.path_info
        if any(url in current_url for url in exempt_urls):
            return self.get_response(request)
            
        # Se o usuário não está autenticado, permite a requisição
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Se é superuser ou staff, permite a requisição
        if request.user.is_superuser or request.user.is_staff:
            return self.get_response(request)
            
        try:
            # Tenta obter a assinatura do usuário
            subscription = UserSubscription.objects.get(user=request.user)
            
            # Se a assinatura não está ativa, redireciona para planos
            if subscription.status != 'active':
                messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
                return redirect('planos')
                
            # Verifica se a assinatura está vencida
            if subscription.end_date and subscription.end_date < timezone.now():
                messages.warning(request, 'Sua assinatura expirou. Por favor, renove seu plano para continuar.')
                return redirect('planos')
                
        except UserSubscription.DoesNotExist:
            # Se não tem assinatura, redireciona para planos
            messages.info(request, 'Você ainda não possui um plano. Por favor, escolha um para continuar.')
            return redirect('planos')
            
        return self.get_response(request)
