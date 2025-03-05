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
            'alterar_plano',
            'webhook_eduzz',
            'verificar_email',
            'static',
            'media',
            'admin',
            'api',
            'stripe',  
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
            # Tenta obter a assinatura do usuário da Eduzz
            subscription = UserSubscription.objects.get(user=request.user)
            
            # Se a assinatura não está ativa, tenta buscar assinatura do Stripe
            if subscription.status != 'active':
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
                        
                    # Caso contrário, redireciona para planos do Stripe em vez da Eduzz
                    messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
                    return redirect('planos_stripe')
                except:
                    # Se der erro ao verificar Stripe, mantém comportamento anterior
                    messages.warning(request, 'Sua assinatura não está ativa. Por favor, escolha um plano para continuar.')
                    return redirect('planos_stripe')
                
            # Verifica se a assinatura está vencida
            if subscription.end_date and subscription.end_date < timezone.now():
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
                        
                    # Caso contrário, redireciona para planos
                    messages.warning(request, 'Sua assinatura expirou. Por favor, renove seu plano para continuar.')
                    return redirect('planos_stripe')
                except:
                    # Se der erro ao verificar Stripe, mantém comportamento anterior
                    messages.warning(request, 'Sua assinatura expirou. Por favor, renove seu plano para continuar.')
                    return redirect('planos_stripe')
                
        except UserSubscription.DoesNotExist:
            # Se não tem assinatura na Eduzz, verifica se tem no Stripe
            try:
                from .models_stripe import StripeSubscription
                stripe_subscription = StripeSubscription.objects.filter(
                    user=request.user, 
                    status__in=['active', 'trialing']
                ).first()
                
                # Se tem assinatura ativa no Stripe, permite acesso
                if stripe_subscription:
                    return self.get_response(request)
            except:
                # Se não conseguir verificar no banco, tenta verificar diretamente na API do Stripe
                try:
                    import stripe
                    from django.conf import settings
                    
                    # Configura a API do Stripe diretamente
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    
                    # Verifica se o usuário tem uma assinatura ativa diretamente na API do Stripe
                    # Isso é uma solução temporária até que as tabelas sejam criadas
                    email = request.user.email
                    logger.info(f"Verificando assinatura para {email} no Stripe")
                    
                    # Busca cliente pelo email
                    customers = stripe.Customer.list(email=email)
                    logger.info(f"Clientes encontrados: {len(customers.data) if customers else 0}")
                    
                    if customers and customers.data:
                        customer = customers.data[0]
                        logger.info(f"Cliente encontrado: {customer.id}")
                        
                        # Busca assinaturas do cliente
                        subscriptions = stripe.Subscription.list(
                            customer=customer.id,
                            status='active',
                            limit=1
                        )
                        logger.info(f"Assinaturas encontradas: {len(subscriptions.data) if subscriptions else 0}")
                        
                        # Se tem assinatura ativa, permite acesso
                        if subscriptions and subscriptions.data:
                            logger.info(f"Assinatura ativa encontrada, permitindo acesso")
                            # Usuário tem assinatura ativa no Stripe
                            return self.get_response(request)
                        else:
                            logger.info("Nenhuma assinatura ativa encontrada")
                    else:
                        logger.info("Nenhum cliente encontrado")
                except Exception as e:
                    logger.error(f"Erro ao verificar assinatura no Stripe: {str(e)}")
                
            # Se não tem assinatura em nenhum dos dois sistemas, redireciona para planos do Stripe
            messages.info(request, 'Você ainda não possui um plano. Por favor, escolha um para continuar.')
            return redirect('planos_stripe')
            
        return self.get_response(request)
