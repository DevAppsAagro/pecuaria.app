from django.db import models
from django.utils import timezone
from datetime import timedelta

class EstacaoMonta(models.Model):
    id = models.AutoField(primary_key=True)
    data_inicio = models.DateField()
    fazenda = models.ForeignKey('Fazenda', on_delete=models.CASCADE)
    lotes = models.ManyToManyField('Lote', related_name='estacoes_monta')
    observacao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Estação {self.id} - {self.fazenda} ({self.data_inicio})"

    class Meta:
        verbose_name = 'Estação de Monta'
        verbose_name_plural = 'Estações de Monta'
        ordering = ['-data_inicio']

class ManejoReproducao(models.Model):
    DIAGNOSTICO_CHOICES = [
        ('PRENHE', 'Prenhe'),
        ('VAZIA', 'Vazia')
    ]
    
    RESULTADO_CHOICES = [
        ('NASCIMENTO', 'Nascimento'),
        ('PERDA_PREPARTO', 'Perda Pré-parto'),
        ('NATIMORTO', 'Natimorto')
    ]

    id = models.AutoField(primary_key=True)
    estacao_monta = models.ForeignKey(EstacaoMonta, on_delete=models.CASCADE)
    lote = models.ForeignKey('Lote', on_delete=models.CASCADE)
    animal = models.ForeignKey('Animal', on_delete=models.CASCADE)
    
    # Campos de Concepção
    data_concepcao = models.DateField(null=True, blank=True)
    previsao_parto = models.DateField(null=True, blank=True)
    
    # Campos de Diagnóstico
    data_diagnostico = models.DateField(null=True, blank=True)
    diagnostico = models.CharField(max_length=10, choices=DIAGNOSTICO_CHOICES, null=True, blank=True)
    
    # Campos de Resultado
    data_resultado = models.DateField(null=True, blank=True)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Calcula previsão de parto se tiver data de concepção
        if self.data_concepcao and not self.diagnostico:
            self.previsao_parto = self.data_concepcao + timedelta(days=283)
        # Remove previsão se diagnóstico for vazia
        elif self.diagnostico == 'VAZIA':
            self.previsao_parto = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Manejo {self.id} - Animal {self.animal} (Estação {self.estacao_monta})"

    class Meta:
        verbose_name = 'Manejo Reprodutivo'
        verbose_name_plural = 'Manejos Reprodutivos'
        ordering = ['-data_concepcao']
