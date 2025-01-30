from django.db import migrations
from django.db.models import F
from decimal import Decimal

def populate_extrato_from_despesas(apps, schema_editor):
    Despesa = apps.get_model('core', 'Despesa')
    ExtratoBancario = apps.get_model('core', 'ExtratoBancario')
    
    # Pega todas as despesas pagas que têm conta bancária
    despesas_pagas = Despesa.objects.filter(
        status='PAGO',
        conta_bancaria__isnull=False,
        data_pagamento__isnull=False
    ).select_related('conta_bancaria', 'contato', 'usuario')
    
    for despesa in despesas_pagas:
        valor_total = despesa.valor_final()
        
        # Cria o registro no extrato bancário
        ExtratoBancario.objects.create(
            conta=despesa.conta_bancaria,
            data=despesa.data_pagamento,
            tipo='despesa',
            descricao=f"Despesa - {despesa.contato.nome}",
            valor=-valor_total,  # Valor negativo para despesa
            saldo_anterior=Decimal('0.00'),  # Será recalculado depois
            saldo_atual=Decimal('0.00'),  # Será recalculado depois
            referencia_id=despesa.id,
            usuario=despesa.usuario
        )

    # Recalcula os saldos para cada conta
    for extrato in ExtratoBancario.objects.all().order_by('conta', 'data', 'created_at'):
        if not hasattr(extrato, '_saldo_anterior'):
            extrato._saldo_anterior = extrato.conta.saldo
        
        extrato.saldo_anterior = extrato._saldo_anterior
        
        # Calcula o novo saldo baseado no tipo de movimentação
        if extrato.tipo in ['venda', 'abate', 'nao_operacional'] and extrato.valor > 0:
            extrato.saldo_atual = extrato.saldo_anterior + extrato.valor
        else:
            extrato.saldo_atual = extrato.saldo_anterior - abs(extrato.valor)
        
        extrato.save()
        
        # Guarda o saldo atual para ser o saldo anterior da próxima movimentação
        extrato._saldo_anterior = extrato.saldo_atual

def reverse_migrate(apps, schema_editor):
    ExtratoBancario = apps.get_model('core', 'ExtratoBancario')
    ExtratoBancario.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0040_despesa_conta_bancaria_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_extrato_from_despesas, reverse_migrate),
    ]
