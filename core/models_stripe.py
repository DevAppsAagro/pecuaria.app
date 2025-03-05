"""
Modelos para armazenar dados da integração com o Stripe
"""
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class StripeCustomer(models.Model):
    """
    Modelo para armazenar os clientes do Stripe relacionados aos usuários Django
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} ({self.stripe_customer_id})"

    class Meta:
        verbose_name = 'Cliente Stripe'
        verbose_name_plural = 'Clientes Stripe'


class StripeProduct(models.Model):
    """
    Modelo para armazenar informações dos produtos do Stripe
    """
    stripe_product_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.stripe_product_id})"

    class Meta:
        verbose_name = 'Produto Stripe'
        verbose_name_plural = 'Produtos Stripe'


class StripePrice(models.Model):
    """
    Modelo para armazenar os preços dos produtos no Stripe
    """
    product = models.ForeignKey(StripeProduct, on_delete=models.CASCADE, related_name='prices')
    stripe_price_id = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=3, default='brl')
    unit_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Valor em reais
    recurring_interval = models.CharField(max_length=10, choices=[
        ('day', 'Diário'),
        ('week', 'Semanal'),
        ('month', 'Mensal'),
        ('year', 'Anual'),
    ], blank=True, null=True)
    recurring_interval_count = models.IntegerField(default=1, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.recurring_interval:
            return f"{self.product.name} - R${self.unit_amount} / {self.get_recurring_interval_display()}"
        return f"{self.product.name} - R${self.unit_amount} (único)"

    class Meta:
        verbose_name = 'Preço Stripe'
        verbose_name_plural = 'Preços Stripe'


class StripeSubscription(models.Model):
    """
    Modelo para armazenar as assinaturas do Stripe
    """
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('past_due', 'Pagamento Atrasado'),
        ('unpaid', 'Não Pago'),
        ('canceled', 'Cancelado'),
        ('incomplete', 'Incompleto'),
        ('incomplete_expired', 'Incompleto Expirado'),
        ('trialing', 'Em Teste'),
    ]

    PLAN_TYPE_CHOICES = [
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
        ('cortesia', 'Cortesia'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    price = models.ForeignKey(StripePrice, on_delete=models.SET_NULL, null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()} ({self.stripe_subscription_id})"

    @property
    def is_active(self):
        """Verifica se a assinatura está ativa"""
        return self.status in ['active', 'trialing']

    @property
    def days_left(self):
        """Retorna dias restantes até o fim do período atual"""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(0, delta.days)
        return 0

    class Meta:
        verbose_name = 'Assinatura Stripe'
        verbose_name_plural = 'Assinaturas Stripe'


class StripeInvoice(models.Model):
    """
    Modelo para armazenar as faturas do Stripe
    """
    STATUS_CHOICES = [
        ('draft', 'Rascunho'),
        ('open', 'Aberta'),
        ('paid', 'Paga'),
        ('uncollectible', 'Não Cobrável'),
        ('void', 'Anulada'),
    ]

    stripe_invoice_id = models.CharField(max_length=100, unique=True)
    stripe_customer_id = models.CharField(max_length=100)
    subscription = models.ForeignKey(StripeSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='brl')
    invoice_date = models.DateTimeField()
    invoice_pdf = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Fatura {self.stripe_invoice_id} - {self.get_status_display()}"

    class Meta:
        verbose_name = 'Fatura Stripe'
        verbose_name_plural = 'Faturas Stripe'


class StripeEvent(models.Model):
    """
    Modelo para armazenar eventos do webhook do Stripe
    """
    stripe_event_id = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=100)
    data = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} ({self.stripe_event_id})"

    class Meta:
        verbose_name = 'Evento Stripe'
        verbose_name_plural = 'Eventos Stripe'
        ordering = ['-created_at']


# Criar automaticamente um cliente Stripe quando um usuário for criado
@receiver(post_save, sender=User)
def create_stripe_customer(sender, instance, created, **kwargs):
    if created:
        # Não criamos o StripeCustomer aqui automaticamente, 
        # isso será feito quando o usuário se inscrever em um plano
        pass


# Garantir que o cliente Stripe seja salvo quando o usuário for salvo
@receiver(post_save, sender=User)
def save_stripe_customer(sender, instance, **kwargs):
    # Apenas atualiza se o StripeCustomer já existir
    if hasattr(instance, 'stripecustomer'):
        instance.stripecustomer.save()
