from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Animal, ContaBancaria, Contato

class Abate(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    comprador = models.ForeignKey(Contato, on_delete=models.PROTECT, verbose_name='Comprador', 
                                limit_choices_to={'tipo': 'CO'}, related_name='abates')
    data = models.DateField('Data do Abate')
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    valor_arroba = models.DecimalField('Valor por @', max_digits=10, decimal_places=2)
    rendimento_padrao = models.DecimalField('Rendimento Padrão (%)', max_digits=5, decimal_places=2, 
                                          help_text='Rendimento padrão de carcaça em porcentagem')
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.PROTECT, verbose_name='Conta Bancária')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Campos de parcelamento
    numero_parcelas = models.IntegerField('Número de Parcelas', default=1)
    intervalo_parcelas = models.IntegerField('Intervalo de Parcelas', default=30)  # 30 dias por padrão
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Abate'
        verbose_name_plural = 'Abates'

    def __str__(self):
        return f"Abate {self.id} - {self.data}"

    def atualizar_status(self):
        """Atualiza o status do abate baseado nas parcelas"""
        from django.db.models import Sum, F
        
        todas_parcelas = self.parcelas.all()
        total_parcelas = todas_parcelas.count()
        if total_parcelas > 0:
            total_pago = todas_parcelas.filter(status='PAGO').count()
            if total_pago == total_parcelas:
                # Todas as parcelas estão pagas
                ultima_parcela = todas_parcelas.filter(status='PAGO').latest('data_pagamento')
                self.status = 'PAGO'
                self.data_pagamento = ultima_parcela.data_pagamento
                print(f"Atualizando abate {self.id} para PAGO com data {self.data_pagamento}")
            elif todas_parcelas.filter(status='VENCIDO').exists():
                self.status = 'VENCIDO'
            else:
                self.status = 'PENDENTE'
            self.save()

class AbateAnimal(models.Model):
    abate = models.ForeignKey(Abate, on_delete=models.CASCADE, related_name='animais')
    animal = models.ForeignKey(Animal, on_delete=models.PROTECT)
    peso_vivo = models.DecimalField('Peso Vivo (kg)', max_digits=10, decimal_places=2)
    rendimento = models.DecimalField('Rendimento (%)', max_digits=5, decimal_places=2,
                                   help_text='Rendimento de carcaça em porcentagem')
    valor_arroba = models.DecimalField('Valor por @', max_digits=10, decimal_places=2)
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['abate', 'animal']
        verbose_name = 'Animal do Abate'
        verbose_name_plural = 'Animais do Abate'

    def peso_arroba(self):
        """Calcula o peso em @ baseado no peso vivo e rendimento"""
        if self.peso_vivo and self.rendimento:
            return (Decimal(str(self.peso_vivo)) * (Decimal(str(self.rendimento)) / 100)) / 15
        return Decimal('0')

    def save(self, *args, **kwargs):
        # Calcula o valor total baseado no peso em @ e valor por @
        if not self.valor_total:
            self.valor_total = self.peso_arroba() * self.valor_arroba
            
        # Atualiza o animal quando abatido
        if not self.pk:  # Apenas na criação
            self.animal.situacao = 'ABATIDO'
            self.animal.data_saida = self.abate.data
            self.animal.valor_venda = self.valor_total
            self.animal.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restaura o animal quando o abate é cancelado
        self.animal.situacao = 'ATIVO'
        self.animal.data_saida = None
        self.animal.valor_venda = None
        self.animal.save()
        super().delete(*args, **kwargs)

class ParcelaAbate(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    abate = models.ForeignKey(Abate, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.IntegerField('Número da Parcela')
    data_vencimento = models.DateField('Data de Vencimento')
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    valor_pago = models.DecimalField('Valor Pago', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)

    class Meta:
        ordering = ['numero']
        verbose_name = 'Parcela do Abate'
        verbose_name_plural = 'Parcelas do Abate'

    def __str__(self):
        return f"Parcela {self.numero} - {self.abate}"

    @property
    def valor_restante(self):
        return self.valor - self.valor_pago

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualiza o status do abate sempre que uma parcela é salva
        self.abate.atualizar_status()

class PagamentoParcelaAbate(models.Model):
    parcela = models.ForeignKey(ParcelaAbate, on_delete=models.CASCADE, related_name='pagamentos')
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    data_pagamento = models.DateField('Data do Pagamento')
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_pagamento']
        verbose_name = 'Pagamento de Parcela do Abate'
        verbose_name_plural = 'Pagamentos de Parcelas do Abate'

    def __str__(self):
        return f"Pagamento {self.id} - Parcela {self.parcela.numero} - Abate {self.parcela.abate.id}"
