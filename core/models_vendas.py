from django.db import models
from django.contrib.auth.models import User
from .models import Animal, ContaBancaria, Contato, Pesagem

class Venda(models.Model):
    TIPO_CHOICES = [
        ('UN', 'Por Unidade'),
        ('KG', 'Por Kg'),
    ]
    
    INTERVALO_PARCELAS_CHOICES = [
        (30, 'Mensal'),
        (15, 'Quinzenal'),
        (7, 'Semanal'),
    ]

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField('Data da Venda')
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    tipo_venda = models.CharField('Tipo de Venda', max_length=2, choices=TIPO_CHOICES)
    valor_unitario = models.DecimalField('Valor Unitário', max_digits=10, decimal_places=2)
    comprador = models.ForeignKey(Contato, on_delete=models.PROTECT, verbose_name='Comprador')
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.PROTECT, verbose_name='Conta Bancária')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Campos de parcelamento
    numero_parcelas = models.IntegerField('Número de Parcelas', default=1)
    intervalo_parcelas = models.IntegerField('Intervalo de Parcelas', choices=INTERVALO_PARCELAS_CHOICES, default=30)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Venda'
        verbose_name_plural = 'Vendas'

    def __str__(self):
        return f"Venda {self.id} - {self.data}"

    @property
    def valor_total(self):
        """Retorna o valor total da venda somando os valores de todos os animais"""
        from django.db.models import Sum
        total = self.animais.aggregate(total=Sum('valor_total'))['total']
        return total if total is not None else 0

    def save(self, *args, **kwargs):
        # Se tiver data de pagamento, atualiza o status para PAGO
        if self.data_pagamento:
            self.status = 'PAGO'
        super().save(*args, **kwargs)

class VendaAnimal(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='animais')
    animal = models.ForeignKey(Animal, on_delete=models.PROTECT)
    peso_venda = models.DecimalField('Peso na Venda', max_digits=10, decimal_places=2, null=True, blank=True)
    valor_kg = models.DecimalField('Valor por Kg', max_digits=10, decimal_places=2, null=True, blank=True)
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['venda', 'animal']
        verbose_name = 'Animal da Venda'
        verbose_name_plural = 'Animais da Venda'

    def save(self, *args, **kwargs):
        # Atualiza o animal quando vendido
        if not self.pk:  # Apenas na criação
            self.animal.situacao = 'VENDIDO'
            self.animal.data_saida = self.venda.data
            self.animal.valor_venda = self.valor_total
            self.animal.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restaura o animal quando a venda é cancelada
        self.animal.situacao = 'ATIVO'
        self.animal.data_saida = None
        self.animal.valor_venda = None
        self.animal.save()
        super().delete(*args, **kwargs)
