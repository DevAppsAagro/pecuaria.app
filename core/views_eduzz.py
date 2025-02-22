from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
import hmac
import hashlib
import logging
import json
from .eduzz_api import EduzzAPI
from .models_eduzz import ClienteLegado, UserSubscription, ClientePlanilha
from datetime import datetime
import pytz
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def eduzz_webhook(request):
    """
    Endpoint para receber notificações da Eduzz
    URL: /api/eduzz/webhook/
    """
    # Verifica a assinatura do webhook
    signature = request.headers.get('X-Eduzz-Signature')
    if not signature:
        return JsonResponse({'error': 'Assinatura não fornecida'}, status=400)

    # Calcula o HMAC da requisição
    calculated_signature = hmac.new(
        settings.EDUZZ_API_KEY.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()

    # Verifica se a assinatura é válida
    if not hmac.compare_digest(calculated_signature, signature):
        return JsonResponse({'error': 'Assinatura inválida'}, status=400)

    # Processa o webhook
    eduzz_api = EduzzAPI()
    success = eduzz_api.process_webhook(request.POST)

    if success:
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Transação não encontrada'}, status=404)

def checkout_page(request):
    """
    Renderiza a página de teste do checkout
    """
    # Log dos settings para debug
    logger.info('Settings da Eduzz:')
    logger.info('- EDUZZ_SOFTWARE_MENSAL_ID: %s', settings.EDUZZ_SOFTWARE_MENSAL_ID)
    logger.info('- EDUZZ_SOFTWARE_ANUAL_ID: %s', settings.EDUZZ_SOFTWARE_ANUAL_ID)
    logger.info('- EDUZZ_SOFTWARE_CORTESIA_ID: %s', settings.EDUZZ_SOFTWARE_CORTESIA_ID)
    
    context = {
        'settings': {
            'EDUZZ_SOFTWARE_MENSAL_ID': settings.EDUZZ_SOFTWARE_MENSAL_ID,
            'EDUZZ_SOFTWARE_ANUAL_ID': settings.EDUZZ_SOFTWARE_ANUAL_ID,
            'EDUZZ_SOFTWARE_CORTESIA_ID': settings.EDUZZ_SOFTWARE_CORTESIA_ID,
        }
    }
    return render(request, 'core/eduzz/checkout.html', context)

@require_http_methods(["POST"])
def create_checkout(request):
    """
    Cria uma nova transação e retorna a URL do checkout
    """
    # Log do request completo
    logger.info('Headers: %s', json.dumps(dict(request.headers)))
    logger.info('POST data: %s', json.dumps(dict(request.POST)))
    
    # Obtém os dados do formulário
    email = request.POST.get('email')
    nome = request.POST.get('nome')
    produto_id = request.POST.get('produto_id')
    valor = request.POST.get('valor')
    tipo_produto = request.POST.get('tipo_produto')

    # Log dos dados recebidos
    logger.info('Dados do checkout:')
    logger.info('- Email: %s', email)
    logger.info('- Nome: %s', nome)
    logger.info('- Produto ID: %s', produto_id)
    logger.info('- Valor: %s', valor)
    logger.info('- Tipo: %s', tipo_produto)

    if not all([email, nome, produto_id, valor, tipo_produto]):
        missing = []
        if not email: missing.append('email')
        if not nome: missing.append('nome')
        if not produto_id: missing.append('produto_id')
        if not valor: missing.append('valor')
        if not tipo_produto: missing.append('tipo_produto')
        
        error_msg = f"Campos faltando: {', '.join(missing)}"
        logger.error(error_msg)
        return JsonResponse({'error': error_msg}, status=400)

    try:
        # Cria a transação na Eduzz
        eduzz_api = EduzzAPI()
        result = eduzz_api.create_transaction(
            email=email,
            nome=nome,
            produto_id=produto_id,
            valor=float(valor),
            tipo_produto=tipo_produto
        )

        if result['success']:
            logger.info('Transação criada com sucesso: %s', result['transaction'].transaction_id)
            return JsonResponse({
                'checkout_url': result['checkout_url'],
                'transaction_id': result['transaction'].transaction_id
            })
        
        logger.error('Erro ao criar transação: %s', result['error'])
        return JsonResponse({'error': result['error']}, status=400)
        
    except Exception as e:
        logger.exception('Erro inesperado ao criar transação:')
        return JsonResponse({'error': str(e)}, status=500)

def planos(request):
    """
    Página principal de planos
    """
    user_email = request.user.email if request.user.is_authenticated else request.GET.get('email', '')
    has_planilha = check_user_has_planilha(user_email) if user_email else False
    
    # Define os planos disponíveis
    plans = [
        {
            'id': settings.EDUZZ_SOFTWARE_MENSAL_ID_3F,
            'name': 'Mensal',
            'period': 'mês',
            'price': 97.00,  # Mensalidade
            'adesao': 497.00 if not has_planilha else 0,
            'total': 594.00 if not has_planilha else 97.00,
            'features': [
                'Acesso a todas as funcionalidades',
                'Suporte via WhatsApp',
                'Atualizações gratuitas',
                'Treinamentos inclusos',
                'Cancele quando quiser'
            ]
        },
        {
            'id': settings.EDUZZ_SOFTWARE_ANUAL_ID_3F,
            'name': 'Anual',
            'period': 'ano',
            'price': 970.00,  # Anualidade (10 meses)
            'adesao': 497.00 if not has_planilha else 0,
            'total': 1467.00 if not has_planilha else 970.00,
            'features': [
                'Todas as funcionalidades do plano mensal',
                '2 meses grátis (pague 10, use 12)',
                'Suporte prioritário',
                'Treinamentos exclusivos',
                'Economia de R$ 194,00/ano'
            ]
        }
    ]
    
    context = {
        'user_email': user_email,
        'has_planilha': has_planilha,
        'plans': plans
    }
    
    return render(request, 'core/planos/planos.html', context)

def verificar_email(request):
    """
    Verifica se o email é de um cliente legado e redireciona para o checkout apropriado
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        plano = request.POST.get('plano')
        
        logger.info('='*50)
        logger.info('VERIFICANDO EMAIL PARA CHECKOUT')
        logger.info('Email: %s', email)
        logger.info('Plano: %s', plano)
        
        # Verifica se é cliente legado
        cliente = ClienteLegado.objects.filter(email=email, ativo=True).first()
        
        # Log do resultado da busca
        if cliente:
            logger.info('Cliente legado encontrado:')
            logger.info('- Nome: %s', cliente.nome)
            logger.info('- ID: %s', cliente.id)
            logger.info('- Data cadastro: %s', cliente.data_cadastro)
            logger.info('- Ativo: %s', cliente.ativo)
        else:
            logger.info('Cliente legado NÃO encontrado')
            
            # Vamos verificar quantos clientes legados existem no total
            total_clientes = ClienteLegado.objects.count()
            clientes_ativos = ClienteLegado.objects.filter(ativo=True).count()
            logger.info('Total de clientes legados: %d', total_clientes)
            logger.info('Total de clientes legados ativos: %d', clientes_ativos)
            
            # Vamos listar alguns clientes para debug
            alguns_clientes = ClienteLegado.objects.all()[:5]
            logger.info('Alguns clientes cadastrados:')
            for c in alguns_clientes:
                logger.info('- %s (%s) - Ativo: %s', c.email, c.nome, c.ativo)
        
        # Define os IDs dos produtos baseado no tipo de cliente
        if plano == 'mensal':
            if cliente:
                # Produto mensal SEM adesão para clientes da planilha
                content_id = settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID
                logger.info('Usando produto mensal SEM adesão: %s', content_id)
            else:
                # Produto mensal COM adesão para novos clientes
                content_id = settings.EDUZZ_SOFTWARE_MENSAL_ID
                logger.info('Usando produto mensal COM adesão: %s', content_id)
        else:  # plano == 'anual'
            if cliente:
                # Produto anual SEM adesão para clientes da planilha
                content_id = settings.EDUZZ_SOFTWARE_ANUAL_SEM_ADESAO_ID
                logger.info('Usando produto anual SEM adesão: %s', content_id)
            else:
                # Produto anual COM adesão para novos clientes
                content_id = settings.EDUZZ_SOFTWARE_ANUAL_ID
                logger.info('Usando produto anual COM adesão: %s', content_id)
        
        logger.info('='*50)
        
        return render(request, 'core/planos/checkout.html', {
            'content_id': content_id,
            'email': email
        })
        
    plano = request.GET.get('plano', 'mensal')
    return render(request, 'core/planos/verificar_email.html', {'plano': plano})

def plano_mensal(request):
    """
    Página do plano mensal com checkout embutido
    """
    url = reverse('verificar_email')
    return redirect(f"{url}?plano=mensal")

def plano_anual(request):
    """
    Página do plano anual com checkout embutido
    """
    url = reverse('verificar_email')
    return redirect(f"{url}?plano=anual")

@login_required
def planos_view(request):
    """View para exibir os planos disponíveis"""
    try:
        # Dados do usuário
        user = request.user
        user_email = user.email or user.username  # Usa o username como fallback se email estiver vazio
        
        logger.info(f"Iniciando carregamento de planos para usuário: {user_email}")
        
        # Lista de planos
        planos = []
        
        # Plano Mensal com adesão
        planos.append({
            'id': settings.EDUZZ_SOFTWARE_MENSAL_ID_3F,
            'name': 'Mensal',
            'price': 97.00,
            'adesao': 497.00,
            'total': 594.00,
            'period': 'mês',
            'features': [
                'Acesso completo ao software',
                'Suporte prioritário',
                'Atualizações gratuitas',
                'Backup automático',
                'Relatórios avançados',
                'Planilha completa incluída'
            ]
        })
        
        # Plano Anual com adesão
        planos.append({
            'id': settings.EDUZZ_SOFTWARE_ANUAL_ID_3F,
            'name': 'Anual',
            'price': 997.00,
            'adesao': 497.00,
            'total': 1494.00,
            'period': 'ano',
            'features': [
                'Acesso completo ao software',
                'Suporte prioritário',
                'Atualizações gratuitas',
                'Backup automático',
                'Relatórios avançados',
                'Planilha completa incluída',
                'Economia de 2 meses'
            ]
        })

        # Verifica se o usuário já tem a planilha
        has_planilha = check_user_has_planilha(user_email)
        logger.info(f"Usuário {user_email} tem planilha? {has_planilha}")
        
        if has_planilha:
            # Substitui os planos pelos sem adesão
            planos = []
            
            # Plano Mensal sem adesão
            planos.append({
                'id': settings.EDUZZ_SOFTWARE_MENSAL_SEM_ADESAO_ID_3F,
                'name': 'Mensal',
                'price': 97.00,
                'period': 'mês',
                'features': [
                    'Acesso completo ao software',
                    'Suporte prioritário',
                    'Atualizações gratuitas',
                    'Backup automático',
                    'Relatórios avançados'
                ]
            })
            
            # Plano Anual sem adesão
            planos.append({
                'id': settings.EDUZZ_SOFTWARE_ANUAL_SEM_ADESAO_ID_3F,
                'name': 'Anual',
                'price': 997.00,
                'period': 'ano',
                'features': [
                    'Acesso completo ao software',
                    'Suporte prioritário',
                    'Atualizações gratuitas',
                    'Backup automático',
                    'Relatórios avançados',
                    'Economia de 2 meses'
                ]
            })

        logger.info(f"Planos carregados: {len(planos)}")
        context = {
            'plans': planos,
            'has_planilha': has_planilha,
            'user_email': user_email
        }
        
        return render(request, 'core/planos/planos.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao carregar planos: {str(e)}", exc_info=True)
        return render(request, 'core/planos/planos.html', {
            'error': str(e),
            'user_email': getattr(request.user, 'username', None)
        })

@login_required
def checkout_plano(request, plan_id):
    """
    Cria uma URL de checkout para o plano selecionado
    """
    user_email = request.user.email if request.user.is_authenticated else request.GET.get('email', '')
    
    if not user_email:
        messages.error(request, 'Email não fornecido')
        return redirect('planos')
    
    # Verifica se o usuário já tem a planilha
    has_planilha = check_user_has_planilha(user_email)
    
    # Mapeamento de IDs de produto para códigos de checkout
    checkout_codes = {
        settings.EDUZZ_SOFTWARE_MENSAL_ID_3F: {
            'with_adesao': '89AQV3B6WD',  # Mensal com adesão
            'without_adesao': '6W4853AO0Z'  # Mensal sem adesão
        },
        settings.EDUZZ_SOFTWARE_ANUAL_ID_3F: {
            'with_adesao': '79772DR49E',  # Anual com adesão
            'without_adesao': 'D0RABOZ29Y'  # Anual sem adesão
        }
    }
    
    # Seleciona o código de checkout correto baseado no plano e se tem planilha
    if plan_id not in checkout_codes:
        messages.error(request, 'Plano inválido')
        return redirect('planos')
        
    content_id = checkout_codes[plan_id]['without_adesao' if has_planilha else 'with_adesao']
    
    context = {
        'content_id': content_id,
        'email': user_email,
    }
    
    return render(request, 'core/planos/checkout.html', context)

@csrf_exempt
def webhook_eduzz(request):
    """
    Webhook para receber notificações da Eduzz
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        
        # Verifica se é uma compra da planilha
        if data.get('product_id') == settings.EDUZZ_PLANILHA_ID:
            # Salva o cliente da planilha
            ClientePlanilha.objects.get_or_create(
                email=data.get('customer_email'),
                defaults={
                    'nome': data.get('customer_name'),
                    'telefone': data.get('customer_phone'),
                    'eduzz_customer_id': data.get('customer_id')
                }
            )
        
        # Obtém o usuário pelo email
        email = data.get('customer', {}).get('email')
        if not email:
            return JsonResponse({'error': 'Email não fornecido'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        
        # Atualiza o perfil do usuário
        usuario_eduzz = user.usuarioeduzz
        usuario_eduzz.eduzz_id = data.get('customer', {}).get('id')
        usuario_eduzz.subscription_id = data.get('subscription', {}).get('id')
        usuario_eduzz.plano_id = data.get('subscription', {}).get('plan_id')
        usuario_eduzz.status = data.get('subscription', {}).get('status')
        usuario_eduzz.data_assinatura = timezone.now()
        usuario_eduzz.data_expiracao = timezone.now() + timedelta(days=30)  # ou usar data do payload
        usuario_eduzz.save()
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def test_eduzz_connection(request):
    """View para testar a conexão com a API da Eduzz"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Acesso não autorizado'}, status=403)
        
    eduzz = EduzzAPI()
    result = eduzz.test_connection()
    
    return JsonResponse(result)

@login_required
def assinatura(request):
    try:
        # Obtém o ID da assinatura do usuário
        subscription_id = request.user.usuarioeduzz.subscription_id
        if not subscription_id:
            messages.warning(request, 'Você ainda não tem uma assinatura ativa.')
            return redirect('planos')

        # Busca os dados da assinatura
        api = EduzzAPI()
        subscription_data = api.get_subscription(subscription_id)
        if not subscription_data:
            messages.error(request, 'Não foi possível obter os dados da sua assinatura.')
            return redirect('planos')

        # Busca o histórico de faturas
        invoices = api.get_subscription_invoices(subscription_id)
        if not invoices:
            invoices = []

        # Organiza as faturas em pagas e pendentes
        paid_invoices = [inv for inv in invoices if inv.get('status') == 'paid']
        pending_invoices = [inv for inv in invoices if inv.get('status') == 'pending']
        
        # Obtém a próxima fatura (a primeira pendente)
        next_invoice = pending_invoices[0] if pending_invoices else None

        context = {
            'subscription': subscription_data,
            'paid_invoices': paid_invoices,
            'pending_invoices': pending_invoices,
            'next_invoice': next_invoice,
        }
        
        return render(request, 'core/assinatura.html', context)
    except Exception as e:
        messages.error(request, f'Erro ao carregar dados da assinatura: {str(e)}')
        return redirect('planos')

@login_required
def alterar_plano(request):
    """Altera o plano da assinatura"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    try:
        # Tenta obter dados do JSON
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_plan_id = data.get('plan_id')
        else:
            # Se não for JSON, tenta obter do POST
            new_plan_id = request.POST.get('plan_id')
        
        try:
            subscription_id = request.user.usuarioeduzz.subscription_id
        except:
            return JsonResponse({'success': False, 'error': 'Usuário não possui assinatura'})
        
        if not all([new_plan_id, subscription_id]):
            return JsonResponse({'success': False, 'error': 'Dados inválidos'})
        
        eduzz = EduzzAPI()
        # Atualiza o plano na Eduzz
        success = eduzz.update_subscription(subscription_id, {
            'plan_id': new_plan_id
        })
        
        if success:
            # Atualiza o plano no banco local
            usuario_eduzz = request.user.usuarioeduzz
            usuario_eduzz.plano_id = new_plan_id
            usuario_eduzz.save()
            
            messages.success(request, "Plano alterado com sucesso!")
            return JsonResponse({'success': True})
        
        return JsonResponse({
            'success': False,
            'error': 'Não foi possível alterar o plano. Tente novamente mais tarde.'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def sync_eduzz_sales(request):
    """
    Sincroniza todas as vendas da Eduzz
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Acesso não autorizado'})
        
    try:
        eduzz = EduzzAPI()
        sales = eduzz.get_all_sales()
        
        for sale in sales:
            # Tenta encontrar usuário pelo email
            try:
                user = User.objects.get(email=sale['email'])
            except User.DoesNotExist:
                continue
                
            # Atualiza ou cria assinatura
            UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'eduzz_subscription_id': sale['subscription_id'],
                    'plan_type': sale['plan_type'],
                    'status': sale['status'],
                    'start_date': sale['start_date'],
                    'end_date': sale['end_date'],
                    'last_payment_date': sale['last_payment_date'],
                    'next_payment_date': sale['next_billing_date']
                }
            )
            
        return JsonResponse({'success': True, 'message': f'Sincronizadas {len(sales)} vendas'})
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar vendas: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

def check_user_has_planilha(email):
    """Verifica se o usuário já comprou a planilha"""
    # Primeiro verifica no banco local
    if ClientePlanilha.objects.filter(email=email).exists():
        return True
        
    # Se não encontrou, busca na API da Eduzz
    api = EduzzAPI()
    purchases = api.get_customer_purchases(email)
    
    # Se encontrou a compra da planilha, salva no banco local
    planilha_id = settings.EDUZZ_PLANILHA_ID
    for purchase in purchases:
        if str(purchase.get('product_id')) == planilha_id:
            ClientePlanilha.objects.create(
                email=email,
                nome=purchase.get('client_name', ''),
                telefone=purchase.get('client_phone', ''),
                eduzz_customer_id=purchase.get('client_id')
            )
            return True
            
    return False
