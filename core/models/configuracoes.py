from django.db import models

class Raca(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Raça'
        verbose_name_plural = 'Raças'
        
    def __str__(self):
        return self.nome

class FinalidadeLote(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Finalidade de Lote'
        verbose_name_plural = 'Finalidades de Lote'
        
    def __str__(self):
        return self.nome

class CategoriaAnimal(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Categoria de Animal'
        verbose_name_plural = 'Categorias de Animais'
        
    def __str__(self):
        return self.nome

class UnidadeMedida(models.Model):
    nome = models.CharField(max_length=50)
    sigla = models.CharField(max_length=10)
    
    class Meta:
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'
        
    def __str__(self):
        return f'{self.nome} ({self.sigla})'

class MotivoMorte(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Motivo de Morte'
        verbose_name_plural = 'Motivos de Morte'
        
    def __str__(self):
        return self.nome

class CategoriaCusto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Categoria de Custo'
        verbose_name_plural = 'Categorias de Custos'
        
    def __str__(self):
        return self.nome

class VariedadeCapim(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Variedade de Capim'
        verbose_name_plural = 'Variedades de Capim'
        
    def __str__(self):
        return self.nome
