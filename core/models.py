from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum
from .models_reproducao import EstacaoMonta, ManejoReproducao

class Fazenda(models.Model):
    ESTADOS_CHOICES = [
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'),
        ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'),
        ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
        ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'),
        ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),
        ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'),
        ('TO', 'Tocantins')
    ]

    nome = models.CharField('Nome da Fazenda', max_length=200)
    arrendada = models.BooleanField('Arrendada', default=False)
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=20, blank=True)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2, choices=ESTADOS_CHOICES)
    area_total = models.DecimalField('Área Total (ha)', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    valor_hectare = models.DecimalField('Valor do Hectare (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    custo_oportunidade = models.DecimalField('Custo de Oportunidade (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    timezone = models.CharField('Fuso Horário', max_length=50, default='America/Sao_Paulo',
        choices=[
            ('America/Manaus', 'Manaus (GMT-4)'),
            ('America/Sao_Paulo', 'São Paulo (GMT-3)'),
            ('America/Belem', 'Belém (GMT-3)'),
            ('America/Rio_Branco', 'Rio Branco (GMT-5)'),
            ('America/Cuiaba', 'Cuiabá (GMT-4)')
        ])

    class Meta:
        verbose_name = 'Fazenda'
        verbose_name_plural = 'Fazendas'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def valor_total(self):
        if not self.arrendada and self.valor_hectare and self.area_total:
            return self.valor_hectare * self.area_total
        return None

class Raca(models.Model):
    nome = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Raça'
        verbose_name_plural = 'Raças'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']

class CategoriaAnimal(models.Model):
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('F', 'Fêmea'),
        ('A', 'Ambos')
    ]
    
    nome = models.CharField(max_length=100)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Categoria de Animal'
        verbose_name_plural = 'Categorias de Animais'
        ordering = ['nome']
        unique_together = ['nome', 'sexo', 'usuario']

    def __str__(self):
        return f'{self.nome} ({self.get_sexo_display()})'

class Animal(models.Model):
    SITUACAO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('VENDIDO', 'Vendido'),
        ('MORTO', 'Morto'),
        ('ABATIDO', 'Abatido')
    ]

    brinco_visual = models.CharField('Brinco Visual', max_length=50, unique=True)
    brinco_eletronico = models.CharField('Brinco Eletrônico', max_length=50, unique=True, blank=True, null=True)
    raca = models.ForeignKey(Raca, on_delete=models.PROTECT, verbose_name='Raça')
    data_nascimento = models.DateField('Data de Nascimento')
    data_entrada = models.DateField('Data de Entrada')
    lote = models.ForeignKey('Lote', on_delete=models.PROTECT, verbose_name='Lote')
    categoria_animal = models.ForeignKey(CategoriaAnimal, on_delete=models.PROTECT, verbose_name='Categoria Animal')
    peso_entrada = models.DecimalField('Peso de Entrada (kg)', max_digits=7, decimal_places=2, null=True, blank=True)
    
    # Campos adicionais no banco
    situacao = models.CharField('Situação', max_length=10, choices=SITUACAO_CHOICES, default='ATIVO')
    fazenda_atual = models.ForeignKey(Fazenda, on_delete=models.PROTECT, verbose_name='Fazenda Atual')
    pasto_atual = models.ForeignKey('Pasto', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Pasto Atual')
    data_saida = models.DateField('Data de Saída', null=True, blank=True)
    valor_compra = models.DecimalField('Valor de Compra (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    custo_fixo = models.DecimalField('Custo Fixo (R$)', max_digits=10, decimal_places=2, default=0)
    custo_variavel = models.DecimalField('Custo Variável (R$)', max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField('Valor Total (R$)', max_digits=10, decimal_places=2, default=0)
    valor_venda = models.DecimalField('Valor de Venda/Abate (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    primeiro_peso = models.DecimalField('Primeiro Peso (kg)', max_digits=7, decimal_places=2, null=True, blank=True)
    data_primeiro_peso = models.DateField('Data do Primeiro Peso', null=True, blank=True)
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Animal'
        verbose_name_plural = 'Animais'
        ordering = ['brinco_visual']

    def __str__(self):
        return f'{self.brinco_visual} - {self.categoria_animal}'

    @property
    def gmd(self):
        """Calcula o GMD (Ganho Médio Diário) do animal"""
        pesagens = self.pesagens.order_by('-data')[:2]  # Pega as duas últimas pesagens
        
        if len(pesagens) >= 2:
            ultima_pesagem = pesagens[0]
            penultima_pesagem = pesagens[1]
            
            dias = (ultima_pesagem.data - penultima_pesagem.data).days
            if dias > 0:
                ganho = ultima_pesagem.peso - penultima_pesagem.peso
                return round(ganho / dias, 2)
            return None  # Retorna None se não houver dias entre as pesagens
        
        # Se não houver pesagens suficientes, tenta calcular com o peso de entrada
        if len(pesagens) == 1 and self.peso_entrada and self.data_entrada:
            ultima_pesagem = pesagens[0]
            dias = (ultima_pesagem.data - self.data_entrada).days
            if dias > 0:
                ganho = ultima_pesagem.peso - self.peso_entrada
                return round(ganho / dias, 2)
        
        return None  # Retorna None se não for possível calcular o GMD

    def get_peso_atual(self):
        """Retorna o peso atual do animal"""
        ultimo_peso = Pesagem.objects.filter(animal=self).order_by('-data').values('peso').first()
        if ultimo_peso:
            return ultimo_peso['peso']
        return self.primeiro_peso or 0

    def save(self, *args, **kwargs):
        # Se é um novo registro e tem peso_entrada, define como primeiro_peso
        if not self.pk and self.peso_entrada:
            self.primeiro_peso = self.peso_entrada
            self.data_primeiro_peso = self.data_entrada
        
        # Atualiza a fazenda atual baseado no lote
        self.fazenda_atual = self.lote.fazenda
        
        # Atualiza o valor total
        self.valor_total = (self.valor_compra or 0) + self.custo_fixo + self.custo_variavel
        
        super().save(*args, **kwargs)

class VariedadeCapim(models.Model):
    nome = models.CharField(max_length=100)
    nome_cientifico = models.CharField('Nome Científico', max_length=100, blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Variedade de Capim'
        verbose_name_plural = 'Variedades de Capim'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']

    def __str__(self):
        return self.nome

class Pasto(models.Model):
    id_pasto = models.CharField('ID do Pasto', max_length=50)
    nome = models.CharField('Nome do Pasto', max_length=100, null=True, blank=True)
    area = models.DecimalField('Área (ha)', max_digits=10, decimal_places=2)
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name='pastos')
    variedade_capim = models.ForeignKey(VariedadeCapim, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Variedade de Capim')
    capacidade_ua = models.DecimalField('Capacidade (UA/ha)', max_digits=10, decimal_places=2)
    coordenadas = models.JSONField('Coordenadas do Polígono')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id_pasto} - {self.fazenda.nome}"
    
    class Meta:
        verbose_name = 'Pasto'
        verbose_name_plural = 'Pastos'
        ordering = ['fazenda', 'id_pasto']

class FinalidadeLote(models.Model):
    nome = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    
    class Meta:
        verbose_name = 'Finalidade de Lote'
        verbose_name_plural = 'Finalidades de Lote'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']  # Evita duplicatas de nome para o mesmo usuário

    def __str__(self):
        return self.nome

class UnidadeMedida(models.Model):
    TIPO_CHOICES = [
        ('PESO', 'Peso'),
        ('AREA', 'Área'),
        ('VOLUME', 'Volume'),
        ('COMPRIMENTO', 'Comprimento'),
        ('TEMPERATURA', 'Temperatura'),
        ('TEMPO', 'Tempo'),
        ('MONETARIO', 'Monetário'),
        ('OUTROS', 'Outros')
    ]
    
    nome = models.CharField('Nome', max_length=100)
    sigla = models.CharField('Sigla', max_length=10)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField('Descrição', blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.nome} ({self.sigla}) - {self.get_tipo_display()}"
    
    class Meta:
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['tipo', 'nome']
        unique_together = ['nome', 'tipo']

class MotivoMorte(models.Model):
    nome = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Motivo de Morte'
        verbose_name_plural = 'Motivos de Morte'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']

    def __str__(self):
        return self.nome

class CategoriaCusto(models.Model):
    TIPO_CHOICES = [
        ('investimento', 'Investimento'),
        ('fixo', 'Custo Fixo'),
        ('variavel', 'Custo Variável'),
    ]
    ALOCACAO_CHOICES = [
        ('fazenda', 'Fazenda'),
        ('lote', 'Lote'),
        ('estoque', 'Estoque'),
        ('maquina', 'Máquina'),
        ('benfeitoria', 'Benfeitoria'),
        ('pastagem', 'Pastagem'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='fixo')
    alocacao = models.CharField('Alocação', max_length=20, choices=ALOCACAO_CHOICES, default='fazenda')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Categoria de Custo'
        verbose_name_plural = 'Categorias de Custos'
        ordering = ['nome']
        unique_together = ['nome', 'usuario']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()} - {self.get_alocacao_display()})"

class SubcategoriaCusto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaCusto, on_delete=models.CASCADE, related_name='subcategorias')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Subcategoria de Custo'
        verbose_name_plural = 'Subcategorias de Custos'
        ordering = ['categoria__nome', 'nome']
        unique_together = ['categoria', 'nome', 'usuario']

    def __str__(self):
        return f"{self.categoria.nome} - {self.nome}"

class Lote(models.Model):
    id_lote = models.CharField('ID do Lote', max_length=50)
    data_criacao = models.DateField('Data de Criação')
    finalidade = models.ForeignKey(FinalidadeLote, on_delete=models.PROTECT, verbose_name='Finalidade do Lote')
    fazenda = models.ForeignKey(Fazenda, on_delete=models.PROTECT, verbose_name='Fazenda')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.id_lote} - {self.finalidade}"
    
    @property
    def quantidade_atual(self):
        """Retorna a quantidade atual de animais ativos no lote"""
        return self.animal_set.filter(situacao='ATIVO').count()

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['id_lote']

class MovimentacaoAnimal(models.Model):
    TIPO_CHOICES = [
        ('LOTE', 'Mudança de Lote'),
        ('PASTO', 'Mudança de Pasto'),
    ]

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=5, choices=TIPO_CHOICES)
    data_movimentacao = models.DateField()
    
    # Campos para movimentação de lote
    lote_origem = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes_origem')
    lote_destino = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes_destino')
    
    # Campos para movimentação de pasto
    pasto_origem = models.ForeignKey(Pasto, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes_origem')
    pasto_destino = models.ForeignKey(Pasto, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes_destino')
    
    motivo = models.CharField('Motivo', max_length=255, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_movimentacao']
        verbose_name = 'Movimentação de Animal'
        verbose_name_plural = 'Movimentações de Animais'

    def clean(self):
        if self.tipo == 'LOTE' and not (self.lote_origem or self.lote_destino):
            raise ValidationError('Para movimentação de lote, especifique o lote de origem ou destino')
        if self.tipo == 'PASTO' and not (self.pasto_origem or self.pasto_destino):
            raise ValidationError('Para movimentação de pasto, especifique o pasto de origem ou destino')
        
        if self.tipo == 'LOTE':
            self.pasto_origem = None
            self.pasto_destino = None
        elif self.tipo == 'PASTO':
            self.lote_origem = None
            self.lote_destino = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Atualiza o lote ou pasto atual do animal
        if self.tipo == 'LOTE' and self.lote_destino:
            self.animal.lote = self.lote_destino
            self.animal.save()
        elif self.tipo == 'PASTO' and self.pasto_destino:
            self.animal.pasto_atual = self.pasto_destino
            self.animal.save()

class Maquina(models.Model):
    id_maquina = models.CharField('ID da Máquina', max_length=50)
    nome = models.CharField('Nome', max_length=100)
    valor_mercado = models.DecimalField('Valor de Mercado', max_digits=10, decimal_places=2)
    valor_compra = models.DecimalField('Valor de Compra', max_digits=10, decimal_places=2)
    valor_residual = models.DecimalField('Valor Residual', max_digits=10, decimal_places=2)
    vida_util = models.IntegerField('Vida Útil (anos)')
    data_aquisicao = models.DateField('Data de Aquisição')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE)

    def depreciacao_anual(self):
        valor_depreciavel = self.valor_compra - self.valor_residual
        return round(valor_depreciavel / self.vida_util, 2)
    
    def depreciacao_mensal(self):
        return round(self.depreciacao_anual() / 12, 2)
    
    def depreciacao_diaria(self):
        return round(self.depreciacao_anual() / 365, 2)

    class Meta:
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'
        ordering = ['id_maquina']

    def __str__(self):
        return f"{self.id_maquina} - {self.nome}"

class Benfeitoria(models.Model):
    id_benfeitoria = models.CharField('ID da Benfeitoria', max_length=50)
    nome = models.CharField('Nome', max_length=100)
    valor_compra = models.DecimalField('Valor de Compra', max_digits=10, decimal_places=2)
    valor_residual = models.DecimalField('Valor Residual', max_digits=10, decimal_places=2, null=True, blank=True)
    vida_util = models.IntegerField('Vida Útil (anos)', null=True, blank=True)
    data_aquisicao = models.DateField('Data de Aquisição', null=True, blank=True)
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    coordenadas = models.JSONField('Coordenadas', null=True, blank=True)
    
    def __str__(self):
        return f"{self.nome} - {self.fazenda.nome}"
    
    class Meta:
        verbose_name = 'Benfeitoria'
        verbose_name_plural = 'Benfeitorias'
        ordering = ['nome']

    def depreciacao_anual(self):
        """Calcula a depreciação anual da benfeitoria"""
        return (self.valor_compra - self.valor_residual) / self.vida_util

    def depreciacao_mensal(self):
        """Calcula a depreciação mensal da benfeitoria"""
        return self.depreciacao_anual() / 12

    def depreciacao_diaria(self):
        """Calcula a depreciação diária da benfeitoria"""
        return self.depreciacao_anual() / 365

class EduzzTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('paid', 'Pago'),
        ('canceled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    product_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.status}"

class ContaBancaria(models.Model):
    TIPO_CHOICES = [
        ('CC', 'Conta Corrente'),
        ('CP', 'Conta Poupança'),
        ('CI', 'Conta Investimento'),
    ]

    banco = models.CharField('Banco', max_length=100)
    agencia = models.CharField('Agência', max_length=20, blank=True, null=True)
    conta = models.CharField('Número da Conta', max_length=20, blank=True, null=True)
    tipo = models.CharField('Tipo de Conta', max_length=2, choices=TIPO_CHOICES, default='CC')
    saldo = models.DecimalField('Saldo Atual', max_digits=15, decimal_places=2, default=0)
    data_saldo = models.DateField('Data do Saldo', default=timezone.now)
    ativa = models.BooleanField('Conta Ativa', default=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fazenda = models.ForeignKey(Fazenda, on_delete=models.SET_NULL, null=True, blank=True)
    data_cadastro = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        ordering = ['banco', 'agencia', 'conta']
        unique_together = ['banco', 'agencia', 'conta', 'usuario']

    def __str__(self):
        return f"{self.banco} - Ag: {self.agencia} - CC: {self.conta}"

    def atualizar_saldo(self, novo_saldo, data=None):
        """Atualiza o saldo da conta com a data fornecida ou data atual"""
        self.saldo = novo_saldo
        self.data_saldo = data or timezone.now().date()
        self.save()
        
        # Cria uma movimentação não operacional para ajuste de saldo
        ExtratoBancario.objects.create(
            conta=self,
            data=self.data_saldo,
            tipo='nao_operacional',
            descricao='Ajuste de Saldo',
            valor=novo_saldo - self.saldo if novo_saldo > self.saldo else -(self.saldo - novo_saldo),
            saldo_anterior=self.saldo,
            saldo_atual=novo_saldo,
            referencia_id=0,
            usuario=self.usuario
        )

class ExtratoBancario(models.Model):
    TIPO_CHOICES = [
        ('despesa', 'Despesa'),
        ('venda', 'Venda'),
        ('abate', 'Abate'),
        ('nao_operacional', 'Não Operacional'),
    ]
    
    conta = models.ForeignKey(ContaBancaria, on_delete=models.CASCADE, related_name='movimentacoes')
    data = models.DateField('Data da Movimentação')
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField('Descrição', max_length=200)
    valor = models.DecimalField('Valor', max_digits=15, decimal_places=2)
    saldo_anterior = models.DecimalField('Saldo Anterior', max_digits=15, decimal_places=2)
    saldo_atual = models.DecimalField('Saldo Atual', max_digits=15, decimal_places=2)
    referencia_id = models.IntegerField('ID de Referência')  # ID da despesa, venda, etc
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Extrato Bancário'
        verbose_name_plural = 'Extratos Bancários'
        ordering = ['-data', '-created_at']
    
    def __str__(self):
        return f"{self.conta} - {self.tipo} - {self.valor} em {self.data}"

    def save(self, *args, **kwargs):
        # Se for uma nova movimentação
        if not self.id:
            self.saldo_anterior = self.conta.saldo
            
            # Calcula o novo saldo baseado no tipo de movimentação
            if self.tipo in ['venda', 'abate', 'nao_operacional'] and self.valor > 0:
                self.saldo_atual = self.saldo_anterior + self.valor
            else:
                self.saldo_atual = self.saldo_anterior - abs(self.valor)
            
            # Atualiza o saldo da conta
            self.conta.saldo = self.saldo_atual
            self.conta.data_saldo = self.data
            self.conta.save()
        
        super().save(*args, **kwargs)

class Pesagem(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='pesagens')
    data = models.DateField('Data da Pesagem')
    peso = models.DecimalField('Peso (kg)', max_digits=7, decimal_places=2)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Pesagem'
        verbose_name_plural = 'Pesagens'
        ordering = ['-data', '-created_at']
    
    def __str__(self):
        return f"{self.animal.brinco_visual} - {self.peso}kg em {self.data}"

class ManejoSanitario(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='manejos_sanitarios')
    data = models.DateField('Data do Manejo')
    insumo = models.CharField('Insumo', max_length=255)
    tipo_manejo = models.CharField('Tipo de Manejo', max_length=255)
    dias_proximo_manejo = models.IntegerField('Dias para Próximo Manejo')
    observacao = models.TextField('Observação', blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Manejo Sanitário'
        verbose_name_plural = 'Manejos Sanitários'
        ordering = ['-data', '-created_at']
    
    def __str__(self):
        return f"{self.animal.brinco_visual} - {self.tipo_manejo} em {self.data}"

class Contato(models.Model):
    TIPO_CHOICES = [
        ('FO', 'Fornecedor'),
        ('FU', 'Funcionário'),
        ('CO', 'Comprador'),
        ('SO', 'Sócio'),
    ]

    nome = models.CharField('Nome', max_length=100)
    tipo = models.CharField('Tipo', max_length=2, choices=TIPO_CHOICES)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    email = models.EmailField('E-mail', blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100)
    uf = models.CharField('UF', max_length=2)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class Despesa(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('VENCE_HOJE', 'Vence Hoje'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    FORMA_PAGAMENTO_CHOICES = [
        ('AV', 'À Vista'),
        ('PR', 'Parcelado'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    numero_nf = models.CharField('Número NF', max_length=50, blank=True, null=True)
    data_emissao = models.DateField('Data de Emissão')
    data_vencimento = models.DateField('Data de Vencimento', null=True, blank=True)
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    contato = models.ForeignKey('Contato', on_delete=models.PROTECT)
    forma_pagamento = models.CharField('Forma de Pagamento', max_length=2, choices=FORMA_PAGAMENTO_CHOICES)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    multa_juros = models.DecimalField('Multa/Juros', max_digits=10, decimal_places=2, default=0)
    desconto = models.DecimalField('Desconto', max_digits=10, decimal_places=2, default=0)
    observacao = models.TextField('Observação', blank=True, null=True)
    arquivo = models.FileField('Arquivo', upload_to='despesas/', blank=True, null=True)
    conta_bancaria = models.ForeignKey('ContaBancaria', on_delete=models.PROTECT, verbose_name='Conta Bancária', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'
        ordering = ['-data_emissao']
    
    def __str__(self):
        return f"{self.contato.nome} - {self.data_emissao}"
    
    def valor_total(self):
        from decimal import Decimal
        return self.itens.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    def valor_final(self):
        return self.valor_total() + self.multa_juros - self.desconto
    
    @property
    def dias_atraso(self):
        from django.utils import timezone
        if self.status == 'VENCIDO' and self.data_vencimento:
            return (timezone.now().date() - self.data_vencimento).days
        return 0
    
    def info_parcelas(self):
        if self.forma_pagamento == 'PR':
            return self.parcelas.all()
        return None
    
    def save(self, *args, **kwargs):
        is_new = not self.id
        old_status = None if is_new else Despesa.objects.get(id=self.id).status
        
        hoje = timezone.now().date()
        
        # Se tem data de pagamento, status é PAGO
        if self.data_pagamento:
            self.status = 'PAGO'
        # Se não tem data de pagamento, verifica vencimento
        elif self.data_vencimento:
            if self.data_vencimento < hoje:
                self.status = 'VENCIDO'
            elif self.data_vencimento == hoje:
                self.status = 'VENCE_HOJE'
            else:
                self.status = 'PENDENTE'
        
        super().save(*args, **kwargs)
        
        # Se a despesa foi paga e tem conta bancária associada
        if self.status == 'PAGO' and self.conta_bancaria and (is_new or old_status != 'PAGO'):
            valor_total = self.valor_final()
            
            # Cria registro no extrato bancário
            ExtratoBancario.objects.create(
                conta=self.conta_bancaria,
                data=self.data_pagamento,
                tipo='despesa',
                descricao=f"Despesa - {self.contato.nome}",
                valor=-valor_total,  # Valor negativo para despesa
                referencia_id=self.id,
                usuario=self.usuario
            )

class ItemDespesa(models.Model):
    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name='itens')
    categoria = models.ForeignKey(CategoriaCusto, on_delete=models.PROTECT)
    subcategoria = models.ForeignKey(SubcategoriaCusto, on_delete=models.PROTECT)
    quantidade = models.DecimalField('Quantidade', max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField('Valor Unitário', max_digits=10, decimal_places=2)
    valor_total = models.DecimalField('Valor Total', max_digits=10, decimal_places=2)
    
    # Campos de destino baseados na alocação
    fazenda_destino = models.ForeignKey(Fazenda, on_delete=models.PROTECT, null=True, blank=True)
    lote_destino = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, blank=True)
    maquina_destino = models.ForeignKey(Maquina, on_delete=models.PROTECT, null=True, blank=True)
    benfeitoria_destino = models.ForeignKey(Benfeitoria, on_delete=models.PROTECT, null=True, blank=True)
    pastagem_destino = models.ForeignKey(Pasto, on_delete=models.PROTECT, null=True, blank=True)
    # estoque_destino será implementado posteriormente

    class Meta:
        verbose_name = 'Item da Despesa'
        verbose_name_plural = 'Itens da Despesa'

    def __str__(self):
        return f"{self.categoria} - {self.valor_total}"

    def save(self, *args, **kwargs):
        # Garante que os valores são Decimal
        self.quantidade = Decimal(str(self.quantidade))
        self.valor_unitario = Decimal(str(self.valor_unitario))
        # Calcula o valor total
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)
        
        # Faz o rateio após salvar
        self.realizar_rateio()

    def realizar_rateio(self):
        # Se for item de estoque, não faz rateio
        if self.categoria.alocacao == 'estoque':
            print(f"Não realizando rateio para item {self.id} - É um item de estoque")
            return
            
        # Inicializa animais como None
        animais = None
        print(f"Realizando rateio para item {self.id} - Categoria: {self.categoria.nome} - Tipo: {self.categoria.tipo} - Alocação: {self.categoria.alocacao}")

        # Verifica se o tipo de alocação é compatível com rateio
        if self.categoria.alocacao not in ['fazenda', 'lote']:
            print(f"Tipo de alocação {self.categoria.alocacao} não é compatível com rateio")
            return

        # Para custos fixos, rateia entre todos os animais da fazenda
        if self.categoria.tipo == 'fixo' and self.fazenda_destino:
            print(f"Rateio fixo para fazenda {self.fazenda_destino.nome}")
            animais = Animal.objects.filter(
                situacao='ATIVO',
                fazenda_atual=self.fazenda_destino,
                data_entrada__lte=self.despesa.data_emissao
            )
            print(f"Encontrados {animais.count()} animais para rateio fixo")
        
        # Para custos variáveis, rateia entre os animais do lote
        elif self.categoria.tipo == 'variavel' and self.lote_destino:
            print(f"Rateio variável para lote {self.lote_destino.id_lote}")
            animais = Animal.objects.filter(
                situacao='ATIVO',
                lote=self.lote_destino,
                data_entrada__lte=self.despesa.data_emissao
            )
            print(f"Encontrados {animais.count()} animais para rateio variável")
        else:
            print(f"Não foi possível realizar rateio - Tipo: {self.categoria.tipo}, Fazenda: {self.fazenda_destino}, Lote: {self.lote_destino}")
            return

        # Se houver animais para ratear
        if animais and animais.exists():
            valor_por_animal = self.valor_total / animais.count()
            print(f"Valor por animal: R$ {valor_por_animal}")
            
            # Registra o rateio para cada animal
            for animal in animais:
                RateioCusto.objects.create(
                    item_despesa=self,
                    animal=animal,
                    valor=valor_por_animal
                )
                print(f"Rateio criado para animal {animal.brinco_visual}: R$ {valor_por_animal}")
        else:
            print("Nenhum animal encontrado para realizar o rateio")

class RateioCusto(models.Model):
    item_despesa = models.ForeignKey(ItemDespesa, on_delete=models.CASCADE)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_rateio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Rateio de Custo'
        verbose_name_plural = 'Rateios de Custos'

    def __str__(self):
        return f"{self.item_despesa} - {self.animal} - R$ {self.valor}"

class ParcelaDespesa(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('VENCE_HOJE', 'Vence Hoje'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.IntegerField('Número da Parcela')
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    multa_juros = models.DecimalField('Multa/Juros', max_digits=10, decimal_places=2, default=0)
    desconto = models.DecimalField('Desconto', max_digits=10, decimal_places=2, default=0)
    observacao = models.TextField('Observação', blank=True, null=True)

    class Meta:
        verbose_name = 'Parcela de Despesa'
        verbose_name_plural = 'Parcelas de Despesa'
        ordering = ['despesa', 'numero']
        unique_together = ['despesa', 'numero']

    def __str__(self):
        return f"Parcela {self.numero} - {self.despesa}"
    
    def valor_final(self):
        return self.valor + self.multa_juros - self.desconto

    def save(self, *args, **kwargs):
        is_new = not self.id
        old_status = None if is_new else ParcelaDespesa.objects.get(id=self.id).status
        
        hoje = timezone.now().date()
        
        # Se tem data de pagamento, status é PAGO
        if self.data_pagamento:
            self.status = 'PAGO'
        # Se não tem data de pagamento, verifica vencimento
        elif self.data_vencimento:
            if self.data_vencimento < hoje:
                self.status = 'VENCIDO'
            elif self.data_vencimento == hoje:
                self.status = 'VENCE_HOJE'
            else:
                self.status = 'PENDENTE'
        
        super().save(*args, **kwargs)
        
        # Atualiza o status da despesa pai se todas as parcelas estiverem pagas
        if self.status == 'PAGO' and (is_new or old_status != 'PAGO'):
            todas_parcelas = self.despesa.parcelas.all()
            todas_pagas = all(p.status == 'PAGO' for p in todas_parcelas)
            
            if todas_pagas:
                self.despesa.status = 'PAGO'
                self.despesa.data_pagamento = max(p.data_pagamento for p in todas_parcelas)
                self.despesa.save()

class MovimentacaoNaoOperacional(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]
    
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    data = models.DateField('Data')
    data_vencimento = models.DateField('Data de Vencimento')
    data_pagamento = models.DateField('Data de Pagamento/Recebimento', null=True, blank=True)
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES)
    conta_bancaria = models.ForeignKey('ContaBancaria', on_delete=models.PROTECT, verbose_name='Conta Bancária')
    fazenda = models.ForeignKey('Fazenda', on_delete=models.PROTECT)
    observacoes = models.TextField('Observações', blank=True)
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_cadastro = models.DateField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Movimentação Não Operacional'
        verbose_name_plural = 'Movimentações Não Operacionais'
        ordering = ['-data', '-data_cadastro']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.valor} - {self.data}"

    def save(self, *args, **kwargs):
        # Se tiver data de pagamento, marca como PAGO
        if self.data_pagamento:
            self.status = 'PAGO'
        # Se não tiver data de pagamento e o status for PAGO, volta para PENDENTE
        elif self.status == 'PAGO':
            self.status = 'PENDENTE'
            
        super().save(*args, **kwargs)
        
        # Se a movimentação foi paga e o status mudou para PAGO
        if self.status == 'PAGO':
            # Cria registro no extrato bancário
            ExtratoBancario.objects.create(
                conta=self.conta_bancaria,
                data=self.data_pagamento,
                tipo='nao_operacional',
                descricao=f"Movimentação Não Operacional - {self.get_tipo_display()}",
                valor=self.valor if self.tipo == 'entrada' else -self.valor,
                referencia_id=self.id,
                usuario=self.usuario
            )
