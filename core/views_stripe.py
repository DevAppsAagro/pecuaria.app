"""
Views para integração com o Stripe
"""
import json
import logging
import stripe
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from .stripe_api import StripeAPI
from .models_stripe import (
    StripeCustomer,
    StripeEvent,
    StripeInvoice,
    StripePrice,
    StripeProduct,
    StripeSubscription,
)

# Configure o logger
logger = logging.getLogger(__name__)

# Inicialize a API do Stripe
stripe_api = StripeAPI()


def planos(request):
    """Página principal de planos"""
    context = {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'stripe_mensal_price_id': settings.STRIPE_MENSAL_PRICE_ID,
        'stripe_anual_price_id': settings.STRIPE_ANUAL_PRICE_ID,
        'email': request.user.email if request.user.is_authenticated else '',
    }
    return render(request, 'core/planos/planos_stripe.html', context)


@login_required
def checkout_session(request, price_id):
    """Criar uma sessão de checkout do Stripe e redirecionar para o Stripe"""
    if not price_id:
        return JsonResponse({'error': 'Preço não informado'}, status=400)
    
    user = request.user
    
    # URLs de sucesso e cancelamento
    success_url = request.build_absolute_uri(reverse('stripe_success'))
    cancel_url = request.build_absolute_uri(reverse('stripe_cancel'))
    
    # Definir o tipo de plano
    if price_id == settings.STRIPE_MENSAL_PRICE_ID:
        plan_type = 'mensal'
    elif price_id == settings.STRIPE_ANUAL_PRICE_ID:
        plan_type = 'anual'
    else:
        return JsonResponse({'error': 'Preço não encontrado'}, status=404)
    
    # Criar a sessão de checkout
    checkout_result = stripe_api.create_checkout_session(
        price_id=price_id,
        customer_email=user.email,
        success_url=success_url,
        cancel_url=cancel_url,
        mode='subscription',
        metadata={
            'user_id': user.id,
            'plan_type': plan_type,
        }
    )
    
    if checkout_result['success']:
        return redirect(checkout_result['url'])
    else:
        logger.error(f"Erro ao criar sessão de checkout: {checkout_result.get('error')}")
        return JsonResponse({'error': 'Erro ao criar sessão de checkout'}, status=500)


def stripe_success(request):
    """Página de sucesso após o checkout"""
    # Adiciona uma mensagem de sucesso na sessão
    messages.success(
        request, 
        "Sua assinatura foi criada com sucesso! Você já pode acessar o sistema."
    )
    
    # Redireciona para a página inicial
    return render(request, 'core/planos/stripe_success.html', {
        'redirect_url': '/'
    })


def stripe_cancel(request):
    """Página de cancelamento após o checkout"""
    return render(request, 'core/planos/stripe_cancel.html', {})


@csrf_exempt
@require_POST
def webhook_stripe(request):
    """Endpoint para receber webhooks do Stripe"""
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not sig_header:
        logger.error("Assinatura não encontrada no header")
        return HttpResponse(status=400)
    
    try:
        # Verificar a assinatura do webhook
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        # Armazenar o evento somente para log
        logger.info(f"Webhook recebido: {event.type}")
        # Logando mais detalhes para debug
        logger.info(f"Dados do evento: {event}")
        
        # Processar o evento
        if event.type == 'checkout.session.completed':
            session = event.data.object
            # Processa a conclusão do checkout e cria assinatura
            handle_checkout_completed(session)
                
        return HttpResponse(status=200)
    
    except Exception as e:
        logger.error(f"Erro ao processar webhook do Stripe: {str(e)}")
        return HttpResponse(status=400)


def handle_checkout_completed(session):
    """
    Processa um evento de checkout.session.completed
    """
    try:
        # Extrair metadados da sessão
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_type = metadata.get('plan_type')
        
        if not user_id:
            logger.error("Checkout sem user_id nos metadados")
            return False
        
        # Buscar usuário
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"Usuário com ID {user_id} não encontrado")
            return False
        
        # Verificar se já existe cliente do Stripe para este usuário
        customer_id = session.get('customer')
        
        if not customer_id:
            logger.error("Checkout sem customer_id")
            return False
        
        # Criar ou atualizar cliente
        customer, created = StripeCustomer.objects.update_or_create(
            user=user,
            defaults={'stripe_customer_id': customer_id}
        )
        logger.info(f"Cliente {'criado' if created else 'atualizado'}: {customer}")
        
        # Buscar detalhes da assinatura (para ter os períodos de início/fim)
        subscription_id = session.get('subscription')
        if subscription_id:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                subscription_data = stripe.Subscription.retrieve(subscription_id)
                
                # Criar ou atualizar assinatura
                subscription, created = StripeSubscription.objects.update_or_create(
                    user=user,
                    defaults={
                        'stripe_subscription_id': subscription_id,
                        'status': subscription_data.status,
                        'plan_type': plan_type or 'mensal',
                        'current_period_start': datetime.fromtimestamp(subscription_data.current_period_start),
                        'current_period_end': datetime.fromtimestamp(subscription_data.current_period_end),
                    }
                )
                
                logger.info(f"Assinatura {'criada' if created else 'atualizada'}: {subscription}")
                return True
            except Exception as e:
                logger.error(f"Erro ao criar assinatura: {str(e)}")
                return False
        else:
            logger.warning("Checkout sem subscription_id")
            return False
    except Exception as e:
        logger.error(f"Erro ao processar checkout: {str(e)}")
        return False


def handle_stripe_event(event):
    """
    Processa eventos do Stripe
    """
    try:
        event_type = event.type
        data = event.data.object
        logger.info(f"Processando evento do Stripe: {event_type}")
        
        # Todo o processamento está temporariamente desativado até que
        # as tabelas do banco de dados sejam criadas corretamente
        
        return True
    
    except Exception as e:
        logger.error(f"Erro ao processar evento {event.type}: {str(e)}")
        return False


def handle_subscription_event(event_type, data):
    """
    Processa eventos relacionados a assinaturas
    """
    subscription_id = data.id
    customer_id = data.customer
    
    # Buscar o cliente no banco
    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)
        user = stripe_customer.user
    except StripeCustomer.DoesNotExist:
        logger.error(f"Cliente {customer_id} não encontrado no banco")
        return False
    
    if event_type == 'customer.subscription.created':
        # Criar ou atualizar assinatura
        create_or_update_subscription(user, data)
        
    elif event_type == 'customer.subscription.updated':
        # Atualizar assinatura existente
        create_or_update_subscription(user, data)
        
    elif event_type == 'customer.subscription.deleted':
        # Cancelar assinatura
        try:
            subscription = StripeSubscription.objects.get(stripe_subscription_id=subscription_id)
            subscription.status = 'canceled'
            subscription.canceled_at = timezone.now()
            subscription.save()
            
            # Atualizar usuário
            # TODO: Implementar lógica para revogar acesso ao usuário quando necessário
            
            logger.info(f"Assinatura {subscription_id} cancelada")
            return True
        except StripeSubscription.DoesNotExist:
            logger.error(f"Assinatura {subscription_id} não encontrada no banco")
            return False
    
    return True


def handle_invoice_event(event_type, data):
    """
    Processa eventos relacionados a faturas
    """
    invoice_id = data.id
    customer_id = data.customer
    
    # Buscar o cliente no banco
    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)
        user = stripe_customer.user
    except StripeCustomer.DoesNotExist:
        logger.error(f"Cliente {customer_id} não encontrado no banco")
        return False
    
    if event_type in ['invoice.created', 'invoice.updated', 'invoice.paid', 'invoice.payment_failed']:
        # Criar ou atualizar fatura
        create_or_update_invoice(user, data)
        
    return True


def create_or_update_subscription(user, subscription_data):
    """
    Cria ou atualiza uma assinatura com os dados do Stripe
    """
    subscription_id = subscription_data.id
    status = subscription_data.status
    
    # Obter dados de preço e produto
    if hasattr(subscription_data, 'items') and subscription_data.items.data:
        price_id = subscription_data.items.data[0].price.id
        product_id = subscription_data.items.data[0].price.product
        
        # Criar ou obter produto e preço localmente
        try:
            price = StripePrice.objects.get(stripe_price_id=price_id)
        except StripePrice.DoesNotExist:
            # Criar produto
            try:
                product = StripeProduct.objects.get(stripe_product_id=product_id)
            except StripeProduct.DoesNotExist:
                product_name = subscription_data.items.data[0].price.product
                product = StripeProduct.objects.create(
                    stripe_product_id=product_id,
                    name=product_name,
                    active=True
                )
            
            # Criar preço
            unit_amount = subscription_data.items.data[0].price.unit_amount / 100
            currency = subscription_data.items.data[0].price.currency
            interval = subscription_data.items.data[0].price.recurring.interval
            
            price = StripePrice.objects.create(
                stripe_price_id=price_id,
                product=product,
                unit_amount=unit_amount,
                currency=currency,
                recurring_interval=interval,
                active=True
            )
    else:
        # Se não conseguirmos obter informações de produto e preço
        price = None
    
    # Criar ou atualizar assinatura
    try:
        subscription = StripeSubscription.objects.get(stripe_subscription_id=subscription_id)
        # Atualizar assinatura existente
        subscription.status = status
        if hasattr(subscription_data, 'current_period_start'):
            subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
        if hasattr(subscription_data, 'current_period_end'):
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)
        if hasattr(subscription_data, 'cancel_at'):
            subscription.cancel_at = datetime.fromtimestamp(subscription_data.cancel_at)
        if hasattr(subscription_data, 'canceled_at'):
            subscription.canceled_at = datetime.fromtimestamp(subscription_data.canceled_at)
        if price:
            subscription.price = price
        subscription.save()
    except StripeSubscription.DoesNotExist:
        # Criar nova assinatura
        subscription = StripeSubscription.objects.create(
            user=user,
            stripe_subscription_id=subscription_id,
            status=status,
            price=price,
            current_period_start=datetime.fromtimestamp(subscription_data.current_period_start) if hasattr(subscription_data, 'current_period_start') else None,
            current_period_end=datetime.fromtimestamp(subscription_data.current_period_end) if hasattr(subscription_data, 'current_period_end') else None,
            cancel_at=datetime.fromtimestamp(subscription_data.cancel_at) if hasattr(subscription_data, 'cancel_at') else None,
            canceled_at=datetime.fromtimestamp(subscription_data.canceled_at) if hasattr(subscription_data, 'canceled_at') else None,
        )
    
    logger.info(f"Assinatura {subscription_id} criada/atualizada para o usuário {user.id}")
    return subscription


def create_or_update_invoice(user, invoice_data):
    """
    Cria ou atualiza uma fatura com os dados do Stripe
    """
    invoice_id = invoice_data.id
    status = invoice_data.status
    
    # Obter assinatura relacionada
    subscription_id = invoice_data.subscription if hasattr(invoice_data, 'subscription') else None
    subscription = None
    if subscription_id:
        try:
            subscription = StripeSubscription.objects.get(stripe_subscription_id=subscription_id)
        except StripeSubscription.DoesNotExist:
            logger.warning(f"Assinatura {subscription_id} não encontrada para a fatura {invoice_id}")
    
    # Criar ou atualizar fatura
    try:
        invoice = StripeInvoice.objects.get(stripe_invoice_id=invoice_id)
        # Atualizar fatura existente
        invoice.status = status
        if hasattr(invoice_data, 'amount_due'):
            invoice.amount_due = Decimal(invoice_data.amount_due) / 100
        if hasattr(invoice_data, 'amount_paid'):
            invoice.amount_paid = Decimal(invoice_data.amount_paid) / 100
        if subscription:
            invoice.subscription = subscription
        invoice.save()
    except StripeInvoice.DoesNotExist:
        # Criar nova fatura
        invoice = StripeInvoice.objects.create(
            user=user,
            stripe_invoice_id=invoice_id,
            subscription=subscription,
            status=status,
            amount_due=Decimal(invoice_data.amount_due) / 100 if hasattr(invoice_data, 'amount_due') else Decimal('0.00'),
            amount_paid=Decimal(invoice_data.amount_paid) / 100 if hasattr(invoice_data, 'amount_paid') else Decimal('0.00'),
        )
    
    logger.info(f"Fatura {invoice_id} criada/atualizada para o usuário {user.id}")
    return invoice


@login_required
def portal_stripe(request):
    """
    Redireciona o usuário para o portal de clientes do Stripe
    """
    # Verificar se o usuário tem um customer no Stripe
    try:
        stripe_customer = StripeCustomer.objects.get(user=request.user)
    except StripeCustomer.DoesNotExist:
        # Se o usuário não tem um customer no Stripe, redirecionamos para a página de planos
        return redirect('planos_stripe')
    
    # URL de retorno após o portal
    return_url = request.build_absolute_uri(reverse('dashboard'))
    
    # Criar a sessão do portal
    try:
        portal_session = stripe_api.create_portal_session(
            customer_id=stripe_customer.stripe_customer_id,
            return_url=return_url
        )
        
        if portal_session['success']:
            return redirect(portal_session['url'])
        else:
            logger.error(f"Erro ao criar sessão do portal: {portal_session.get('error')}")
            return JsonResponse({'error': 'Erro ao criar sessão do portal'}, status=500)
    except Exception as e:
        logger.error(f"Erro ao criar sessão do portal: {str(e)}")
        return JsonResponse({'error': 'Erro ao criar sessão do portal'}, status=500)


@login_required
def cortesia(request):
    """
    Cria uma assinatura de cortesia para o usuário
    """
    user = request.user
    
    # Verificar se o usuário já tem uma assinatura ativa
    existing_subscription = StripeSubscription.objects.filter(
        user=user, 
        status__in=['active', 'trialing']
    ).exists()
    
    if existing_subscription:
        # Usuário já tem uma assinatura ativa
        return redirect('dashboard')
    
    # Verificar se o usuário já tem um customer no Stripe
    try:
        stripe_customer = StripeCustomer.objects.get(user=user)
    except StripeCustomer.DoesNotExist:
        # Criar um novo customer no Stripe
        customer_result = stripe_api.create_customer(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.email,
            metadata={'user_id': user.id}
        )
        
        if customer_result['success']:
            stripe_customer = StripeCustomer.objects.create(
                user=user,
                stripe_customer_id=customer_result['customer_id']
            )
        else:
            logger.error(f"Erro ao criar cliente no Stripe: {customer_result.get('error')}")
            return JsonResponse({'error': 'Erro ao criar cliente no Stripe'}, status=500)
    
    # Criar uma assinatura de cortesia (trial)
    trial_end = datetime.now() + timedelta(days=7)  # 7 dias de trial
    
    try:
        # Verificar se o preço existe no banco
        try:
            price = StripePrice.objects.get(stripe_price_id=settings.STRIPE_MENSAL_PRICE_ID)
        except StripePrice.DoesNotExist:
            # Criar produto e preço localmente se não existirem
            try:
                product = StripeProduct.objects.get(name='Mensal')
            except StripeProduct.DoesNotExist:
                product = StripeProduct.objects.create(
                    stripe_product_id='prod_trial',
                    name='Mensal',
                    active=True
                )
            
            price = StripePrice.objects.create(
                stripe_price_id=settings.STRIPE_MENSAL_PRICE_ID,
                product=product,
                unit_amount=Decimal('49.90'),
                currency='brl',
                recurring_interval='month',
                active=True
            )
        
        # Criar assinatura diretamente no banco (sem cobrar)
        subscription = StripeSubscription.objects.create(
            user=user,
            stripe_subscription_id='sub_trial',
            status='trialing',
            price=price,
            current_period_start=datetime.now(),
            current_period_end=trial_end,
        )
        
        # Redirecionar para a página de sucesso
        return redirect('stripe_success')
    
    except Exception as e:
        logger.error(f"Erro ao criar assinatura de cortesia: {str(e)}")
        return JsonResponse({'error': 'Erro ao criar assinatura de cortesia'}, status=500)


def stripe_webhook_check(request):
    """
    Endpoint para verificar se o webhook está corretamente configurado
    """
    return HttpResponse("Webhook check", status=200)
