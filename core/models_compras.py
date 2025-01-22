from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from .models import Animal, Contato, ContaBancaria

class Compra(models.Model):
    TIPO_COMPRA_CHOICES = [
        ('UN', 'Por Unidade'),
        ('KG', 'Por Kg')
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
        ('VENCE_HOJE', 'Vence Hoje'),
        ('CANCELADO', 'Cancelado'),
    ]

    data = models.DateField('Data da Compra')
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    tipo_compra = models.CharField('Tipo de Compra', max_length=2, choices=TIPO_COMPRA_CHOICES)
    valor_unitario = models.DecimalField('Valor Unitário', max_digits=10, decimal_places=2)
    vendedor = models.ForeignKey(Contato, on_delete=models.PROTECT, verbose_name='Vendedor')
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.PROTECT, verbose_name='Conta Bancária')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Campos de parcelamento
    numero_parcelas = models.IntegerField('Número de Parcelas', default=1)
    intervalo_parcelas = models.IntegerField('Intervalo de Parcelas', choices=INTERVALO_PARCELAS_CHOICES, default=30)
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-data', '-data_cadastro']

    def __str__(self):
        return f'Compra - {self.data}'

    def save(self, *args, **kwargs):
        # Atualiza o status baseado nas datas
        from datetime import date
        
        if self.data_pagamento:
            self.status = 'PAGO'
        else:
            hoje = date.today()
            if self.data_vencimento < hoje:
                self.status = 'VENCIDO'
            elif self.data_vencimento == hoje:
                self.status = 'VENCE_HOJE'
            else:
                self.status = 'PENDENTE'
        
        super().save(*args, **kwargs)

class CompraAnimal(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='animais')
    animal = models.ForeignKey(Animal, on_delete=models.PROTECT)
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Animal da Compra'
        verbose_name_plural = 'Animais da Compra'
        unique_together = ['compra', 'animal']

    def __str__(self):
        return f'{self.animal} - {self.compra}'

    def save(self, *args, **kwargs):
        # Atualiza o valor de compra do animal
        self.animal.valor_compra = self.valor_total
        self.animal.save()
        super().save(*args, **kwargs)
