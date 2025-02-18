from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
import hmac
import hashlib
import logging
import json
from .eduzz_api import EduzzAPI
from .models_eduzz import ClienteLegado

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
    return render(request, 'core/planos/planos.html')

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
