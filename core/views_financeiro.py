from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal

from .models import ContaBancaria, Despesa, MovimentacaoNaoOperacional
from .models_vendas import Venda
from .models_compras import Compra
from .models_abates import Abate

@login_required
def atualizar_saldos_contas_bancarias(request):
    """Função para atualizar os saldos de todas as contas bancárias do usuário"""
    contas = ContaBancaria.objects.filter(usuario=request.user)
    contas_atualizadas = 0
    
    for conta in contas:
        # Inicializa o saldo com o saldo inicial
        saldo = conta.saldo_inicial or Decimal('0.00')
        
        # Despesas
        despesas = Despesa.objects.filter(
            usuario=request.user,
            conta_bancaria=conta,
            status='PAGO',
            data_pagamento__isnull=False
        )
        total_despesas = sum(despesa.valor_final() for despesa in despesas)
        
        # Vendas 
        vendas = Venda.objects.filter(
            usuario=request.user,
            conta_bancaria=conta,
            status='PAGO',
            data_pagamento__isnull=False
        )
        total_vendas = sum(venda.valor_total for venda in vendas)
        
        # Compras
        compras = Compra.objects.filter(
            usuario=request.user,
            conta_bancaria=conta,
            status='PAGO',
            data_pagamento__isnull=False
        )
        total_compras = sum(compra.valor_total for compra in compras)
        
        # Abates
        abates = Abate.objects.filter(
            usuario=request.user,
            conta_bancaria=conta,
            status='PAGO',
            data_pagamento__isnull=False
        )
        total_abates = sum(abate.valor_total for abate in abates)
        
        # Movimentações não operacionais
        nao_operacionais = MovimentacaoNaoOperacional.objects.filter(
            usuario=request.user,
            conta_bancaria=conta,
            status='PAGO',
            data_pagamento__isnull=False
        )
        
        total_entrada_nao_op = sum(mov.valor for mov in nao_operacionais if mov.tipo == 'entrada')
        total_saida_nao_op = sum(mov.valor for mov in nao_operacionais if mov.tipo == 'saida')
        
        # Calcula o saldo final
        saldo_calculado = (
            saldo + 
            total_vendas + 
            total_abates + 
            total_entrada_nao_op - 
            total_despesas - 
            total_compras - 
            total_saida_nao_op
        )
        
        # Atualiza o saldo no banco de dados apenas se houver mudança
        if conta.saldo != saldo_calculado:
            conta.saldo = saldo_calculado
            conta.save(update_fields=['saldo'])
            contas_atualizadas += 1
    
    messages.success(request, f'{contas_atualizadas} contas tiveram seus saldos atualizados')
    return redirect('contas_bancarias_list')
