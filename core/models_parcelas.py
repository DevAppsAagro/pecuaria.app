from django.db import models
from django.core.exceptions import ValidationError
from .models_compras import Compra
from .models import ContaBancaria
from datetime import date

class ParcelaCompra(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PARCIAL', 'Parcialmente Pago'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
    ]

    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.IntegerField()  # Número da parcela (1, 2, 3, etc.)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    
    class Meta:
        ordering = ['data_vencimento']
        unique_together = ['compra', 'numero']

    def __str__(self):
        return f"Parcela {self.numero}/{self.compra.numero_parcelas} - R${self.valor}"

    @property
    def valor_pago(self):
        return sum(pagamento.valor for pagamento in self.pagamentos.all())

    @property
    def valor_restante(self):
        return self.valor - self.valor_pago

    def atualizar_status(self):
        """Atualiza o status da parcela com base nos pagamentos realizados"""
        valor_pago = self.valor_pago
        
        if valor_pago >= self.valor:
            novo_status = 'PAGO'
        elif valor_pago > 0:
            novo_status = 'PARCIAL'
        elif self.data_vencimento < date.today():
            novo_status = 'VENCIDO'
        else:
            novo_status = 'PENDENTE'
        
        # Só atualiza se o status mudou para evitar recursão
        if self.status != novo_status:
            self.status = novo_status
            models.Model.save(self, update_fields=['status'])

    def save(self, *args, **kwargs):
        # Primeiro salva a parcela
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Depois atualiza o status se não for uma nova parcela
        if not is_new and 'update_fields' not in kwargs:
            self.atualizar_status()


class PagamentoParcela(models.Model):
    parcela = models.ForeignKey(ParcelaCompra, on_delete=models.CASCADE, related_name='pagamentos')
    data_pagamento = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.PROTECT)
    observacao = models.TextField(blank=True, null=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_pagamento']

    def clean(self):
        # Valida se o valor do pagamento não excede o valor restante da parcela
        if hasattr(self, 'parcela'):
            valor_disponivel = self.parcela.valor_restante
            if self.valor > valor_disponivel:
                raise ValidationError({
                    'valor': f'O valor do pagamento (R${self.valor}) excede o valor restante da parcela (R${valor_disponivel})'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # Atualiza o status da parcela
        self.parcela.atualizar_status()
