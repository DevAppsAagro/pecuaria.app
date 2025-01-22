from django.db import models
from django.contrib.auth.models import User
from .models import (
    CategoriaCusto, SubcategoriaCusto, UnidadeMedida,
    Despesa, Lote, Pasto, Animal
)
from decimal import Decimal
from django.core.validators import MinValueValidator

class Insumo(models.Model):
    nome = models.CharField('Nome do Insumo', max_length=100)
    categoria = models.ForeignKey(CategoriaCusto, on_delete=models.PROTECT, 
                                limit_choices_to={'alocacao': 'estoque'})
    subcategoria = models.ForeignKey(SubcategoriaCusto, on_delete=models.PROTECT)
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT)
    saldo_estoque = models.DecimalField('Saldo em Estoque', max_digits=10, decimal_places=2, default=0)
    preco_medio = models.DecimalField('Preço Médio', max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2, default=0)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']  # Evita duplicatas de nome para o mesmo usuário

    def __str__(self):
        return f"{self.nome} ({self.unidade_medida.sigla})"

    def atualizar_valor_total(self):
        """Atualiza o valor total do estoque baseado no saldo e preço médio"""
        self.valor_total = self.saldo_estoque * self.preco_medio
        self.save()

class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
        ('SN', 'Saída Nutrição')
    ]
    
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='movimentacoes')
    tipo = models.CharField('Tipo', max_length=2, choices=TIPO_CHOICES)
    data = models.DateField('Data')
    quantidade = models.DecimalField('Quantidade', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    valor_unitario = models.DecimalField('Valor Unitário', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2)
    despesa = models.ForeignKey('Despesa', on_delete=models.SET_NULL, null=True, blank=True)
    lote = models.ForeignKey('Lote', on_delete=models.SET_NULL, null=True, blank=True)
    pasto = models.ForeignKey('Pasto', on_delete=models.SET_NULL, null=True, blank=True)
    destino_lote = models.ForeignKey('Lote', on_delete=models.SET_NULL, null=True, blank=True, related_name='destino_movimentacoes')
    consumo_pv = models.DecimalField('Consumo % Peso Vivo', max_digits=5, decimal_places=2, null=True, blank=True)
    observacao = models.TextField('Observação', blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data', '-data_cadastro']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.insumo.nome} - {self.data}"

    def save(self, *args, **kwargs):
        # Calcula o valor total
        self.valor_total = self.quantidade * self.valor_unitario
        
        # Salva a movimentação
        super().save(*args, **kwargs)
        
        # Atualiza o estoque do insumo
        insumo = self.insumo
        if self.tipo == 'E':  # Entrada
            novo_saldo = insumo.saldo_estoque + self.quantidade
            # Calcula novo preço médio
            valor_total_anterior = insumo.saldo_estoque * insumo.preco_medio
            novo_valor_total = valor_total_anterior + self.valor_total
            insumo.preco_medio = novo_valor_total / novo_saldo if novo_saldo > 0 else 0
            insumo.saldo_estoque = novo_saldo
        else:  # Saída ou Saída Nutrição
            insumo.saldo_estoque = insumo.saldo_estoque - self.quantidade
        
        insumo.atualizar_valor_total()

class RateioMovimentacao(models.Model):
    movimentacao = models.ForeignKey(MovimentacaoEstoque, on_delete=models.CASCADE)
    animal = models.ForeignKey('Animal', on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rateio_movimentacao'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Rateio {self.movimentacao} - Animal {self.animal}"
