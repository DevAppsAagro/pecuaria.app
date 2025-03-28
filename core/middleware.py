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
            'success',  
            'cancel',   
            'password_reset',
            'planos-stripe',
            'webhook',  
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
            import stripe
            from django.conf import settings
            
            # Configurar chave API
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Verifica se o usuário está saindo da página de sucesso do Stripe
            is_from_success = 'stripe/success' in request.META.get('HTTP_REFERER', '')
            
            # Se veio da página de sucesso, permite acesso temporário
            # isso dá tempo para o webhook processar a assinatura
            if is_from_success:
                logger.info(f"Usuário {request.user.email} veio da página de sucesso do Stripe, permitindo acesso temporário")
                request.session['from_stripe_success'] = True
                request.session['stripe_success_time'] = timezone.now().timestamp()
                return self.get_response(request)
            
            # Se tem flag temporária de sucesso do Stripe e ainda está no período de graça (5 minutos)
            from_success = request.session.get('from_stripe_success', False)
            success_time = request.session.get('stripe_success_time', 0)
            current_time = timezone.now().timestamp()
            
            if from_success and (current_time - success_time < 300):  # 5 minutos
                logger.info(f"Usuário {request.user.email} está no período de graça após sucesso do Stripe")
                return self.get_response(request)
            
            # Verificar se existe cache da assinatura na sessão
            subscription_cache = request.session.get('stripe_subscription_cache', {})
            subscription_cache_time = subscription_cache.get('timestamp', 0)
            has_active_subscription = subscription_cache.get('active', False)
            
            # Cache válido por 24 horas (86400 segundos) em vez de 1 hora
            cache_validity_period = 86400  # 24 horas
            
            # Verificar se o cache é válido
            if current_time - subscription_cache_time < cache_validity_period:
                logger.info(f"Usando cache de assinatura para o usuário {request.user.email}")
                if has_active_subscription:
                    return self.get_response(request)
                else:
                    # Se não tem assinatura ativa no cache, redireciona para página de planos
                    messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
                    return redirect('planos')
            else:
                # Cache expirado ou não existe, verificar diretamente no Stripe
                # Mas primeiro, verificar se já fizemos essa verificação recentemente para esta sessão
                last_stripe_check = request.session.get('last_stripe_check', 0)
                stripe_check_cooldown = 300  # 5 minutos de cooldown entre verificações diretas
                
                if current_time - last_stripe_check < stripe_check_cooldown:
                    logger.info(f"Verificação do Stripe em cooldown para {request.user.email}, usando último resultado conhecido")
                    if has_active_subscription:
                        return self.get_response(request)
                    else:
                        messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
                        return redirect('planos')
                
                # Registrar que estamos fazendo uma verificação direta agora
                request.session['last_stripe_check'] = current_time
                
                has_active_subscription = False
                try:
                    # Buscar cliente pelo email
                    customers = stripe.Customer.list(email=request.user.email)
                    
                    if customers and customers.data:
                        customer = customers.data[0]
                        logger.info(f"Cliente Stripe encontrado: {customer.id}")
                        
                        # Verificar assinaturas do cliente
                        subscriptions = stripe.Subscription.list(
                            customer=customer.id,
                            status='active'
                        )
                        
                        has_active_subscription = subscriptions and len(subscriptions.data) > 0
                        logger.info(f"Assinaturas ativas encontradas: {len(subscriptions.data) if subscriptions else 0}")
                        
                        # Atualizar o cache na sessão com validade de 24 horas
                        request.session['stripe_subscription_cache'] = {
                            'timestamp': current_time,
                            'active': has_active_subscription,
                            'customer_id': customer.id if has_active_subscription else None,
                            'subscription_id': subscriptions.data[0].id if has_active_subscription and subscriptions.data else None
                        }
                except Exception as e:
                    logger.error(f"Erro ao verificar assinatura diretamente no Stripe: {str(e)}")
                    # Em caso de erro, manter o cache anterior se existir
                    if subscription_cache and has_active_subscription:
                        logger.info(f"Mantendo cache anterior devido a erro na API do Stripe para {request.user.email}")
                        return self.get_response(request)
            
            # Se tem assinatura ativa no Stripe, permite acesso
            if has_active_subscription:
                return self.get_response(request)
                
            # Caso contrário, redireciona para página de planos
            messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
            return redirect('planos')
        except Exception as e:
            logger.error(f"Erro ao verificar assinatura do Stripe: {str(e)}")
            messages.warning(request, 'Não foi possível verificar sua assinatura. Por favor, entre em contato com o suporte.')
            return redirect('planos')
