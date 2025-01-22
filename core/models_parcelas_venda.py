from django.db import models
from django.utils import timezone
from decimal import Decimal
from .models_vendas import Venda

class ParcelaVenda(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PARCIAL', 'Parcial'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
    ]

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='parcelas')
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
        return sum(pagamento.valor for pagamento in self.pagamentos_venda.all())

    @property
    def valor_restante(self):
        return self.valor - self.valor_pago

    def save(self, *args, **kwargs):
        # Atualiza o status com base no vencimento e pagamentos
        if self.valor_pago >= self.valor:
            self.status = 'PAGO'
        elif self.valor_pago > 0:
            self.status = 'PARCIAL'
        elif self.data_vencimento < timezone.now().date():
            self.status = 'VENCIDO'
        else:
            self.status = 'PENDENTE'
        super().save(*args, **kwargs)
