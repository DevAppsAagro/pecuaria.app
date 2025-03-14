from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F
from .models_parcelas import ParcelaCompra, PagamentoParcela
from .forms_parcelas import PagamentoParcelaForm

@login_required
def registrar_pagamento(request, parcela_id):
    parcela = get_object_or_404(ParcelaCompra, id=parcela_id, compra__usuario=request.user)
    
    if request.method == 'POST':
        form = PagamentoParcelaForm(parcela, request.POST)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.parcela = parcela
            pagamento.save()
            
            # Atualizar status da parcela
            parcela.atualizar_status()
            
            # Verificar se todas as parcelas estão pagas e atualizar a compra
            compra = parcela.compra
            todas_parcelas = compra.parcelas.all()
            todas_pagas = todas_parcelas.filter(status='PAGO').count() == todas_parcelas.count()
            
            if todas_pagas and not compra.data_pagamento:
                # Se todas as parcelas estão pagas e a compra ainda não tem data de pagamento
                compra.data_pagamento = timezone.now().date()
                compra.status = 'PAGO'
                compra.save()
            
            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('compras_detalhe', pk=parcela.compra.pk)
    else:
        form = PagamentoParcelaForm(parcela)
    
    context = {
        'form': form,
        'parcela': parcela,
        'pagamentos': parcela.pagamentos.all(),
    }
    return render(request, 'core/parcelas/pagamento_form.html', context)

@login_required
def historico_pagamentos(request, parcela_id):
    parcela = get_object_or_404(ParcelaCompra, id=parcela_id, compra__usuario=request.user)
    context = {
        'parcela': parcela,
        'pagamentos': parcela.pagamentos.all(),
    }
    return render(request, 'core/parcelas/historico_pagamentos.html', context)
