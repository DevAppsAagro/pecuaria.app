from django.db import models
from .models_parcelas_venda import ParcelaVenda

class PagamentoVenda(models.Model):
    parcela = models.ForeignKey(ParcelaVenda, on_delete=models.CASCADE, related_name='pagamentos_venda')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateField()
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_pagamento']
        verbose_name = 'Pagamento de Venda'
        verbose_name_plural = 'Pagamentos de Vendas'

    def __str__(self):
        return f'Pagamento de R$ {self.valor} da parcela {self.parcela.numero} da venda {self.parcela.venda.id}'
