from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class ClienteLegado(models.Model):
    """
    Modelo para armazenar clientes legados importados da planilha antiga
    """
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=200)
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2)
    id_eduzz_antigo = models.CharField(max_length=100, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} ({self.email})"

    class Meta:
        verbose_name = 'Cliente Legado'
        verbose_name_plural = 'Clientes Legados'
        ordering = ['nome']

class EduzzTransaction(models.Model):
    """
    Modelo para armazenar transações da Eduzz
    """
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('paid', 'Pago'),
        ('canceled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    ]

    PLAN_CHOICES = [
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
        ('cortesia', 'Cortesia'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    nome = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    product_id = models.CharField(max_length=100)
    plano = models.CharField(max_length=20, choices=PLAN_CHOICES, default='mensal')
    valor_original = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_expiracao = models.DateField(null=True, blank=True)
    data_pagamento = models.DateTimeField(null=True, blank=True)
    is_legado = models.BooleanField(default=False, help_text="Indica se é um cliente que migrou da planilha")
    cliente_legado = models.ForeignKey(ClienteLegado, on_delete=models.SET_NULL, null=True, blank=True)
    webhook_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.plano} ({self.status})"

    class Meta:
        verbose_name = 'Transação Eduzz'
        verbose_name_plural = 'Transações Eduzz'
        ordering = ['-data_pagamento']

    def save(self, *args, **kwargs):
        # Se for um cliente legado, aplicar desconto na adesão
        if self.cliente_legado:
            # Aqui você pode adicionar lógica específica para desconto na adesão
            pass
        super().save(*args, **kwargs)
