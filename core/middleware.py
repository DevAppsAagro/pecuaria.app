from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
from .models import Fazenda
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

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
            'register',
            'verificar_email',
            'static',
            'media',
            'admin',
            'api',
            'stripe',  
            'checkout',
            'password_reset',
            'planos-stripe',
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
            # Verifica se existe assinatura ativa no Stripe
            from .models_stripe import StripeSubscription
            stripe_subscription = StripeSubscription.objects.filter(
                user=request.user, 
                status__in=['active', 'trialing']
            ).first()
            
            # Se tem assinatura ativa no Stripe, permite acesso
            if stripe_subscription:
                return self.get_response(request)
                
            # Caso contrário, redireciona para página de planos
            messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
            return redirect('planos')
        except Exception as e:
            logger.error(f"Erro ao verificar assinatura do Stripe: {str(e)}")
            messages.warning(request, 'Não foi possível verificar sua assinatura. Por favor, entre em contato com o suporte.')
            return redirect('planos')
