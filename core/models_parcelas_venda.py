from django.db import models
from django.utils import timezone
from decimal import Decimal

class ParcelaVenda(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PARCIAL', 'Parcial'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
    ]

    venda = models.ForeignKey('core.Venda', on_delete=models.CASCADE, related_name='parcelas')
    numero = models.IntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')

    class Meta:
        ordering = ['numero']
        unique_together = ['venda', 'numero']
        verbose_name = 'Parcela de Venda'
        verbose_name_plural = 'Parcelas de Vendas'

    def __str__(self):
        return f'Parcela {self.numero} da venda {self.venda.id}'

    @property
    def valor_pago(self):
        """Retorna o valor total pago nesta parcela"""
        if not self.pk:  # Se a parcela ainda não foi salva
            return Decimal('0')
        # Importa aqui para evitar importação circular
        from .models_pagamentos_venda import PagamentoVenda
        return PagamentoVenda.objects.filter(parcela=self).aggregate(
            total=models.Sum('valor')
        )['total'] or Decimal('0')

    @property
    def valor_restante(self):
        """Retorna o valor restante a ser pago nesta parcela"""
        return self.valor - self.valor_pago

    def atualizar_status(self):
        """Atualiza o status da parcela com base nos pagamentos"""
        valor_pago = self.valor_pago
        
        if valor_pago >= self.valor:
            self.status = 'PAGO'
        elif valor_pago > 0:
            self.status = 'PARCIAL'
        elif self.data_vencimento < timezone.now().date():
            self.status = 'VENCIDO'
        else:
            self.status = 'PENDENTE'

    def save(self, *args, **kwargs):
        # Atualiza o status antes de salvar
        self.atualizar_status()
        super().save(*args, **kwargs)
