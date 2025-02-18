from django.contrib import admin
from .models import Fazenda, Animal, UnidadeMedida
from .models_eduzz import ClienteLegado, EduzzTransaction

@admin.register(Fazenda)
class FazendaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'usuario', 'cidade', 'estado', 'area_total', 'arrendada']
    list_filter = ['estado', 'arrendada']
    search_fields = ['nome', 'cidade']

@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ['brinco_visual', 'brinco_eletronico', 'raca', 'categoria_animal', 'lote', 'fazenda_atual', 'situacao']
    list_filter = ['situacao', 'raca', 'categoria_animal', 'fazenda_atual']
    search_fields = ['brinco_visual', 'brinco_eletronico']
    readonly_fields = ['primeiro_peso', 'data_primeiro_peso', 'valor_total']
    fieldsets = (
        ('Identificação', {
            'fields': ('brinco_visual', 'brinco_eletronico', 'raca', 'categoria_animal')
        }),
        ('Informações de Entrada', {
            'fields': ('data_nascimento', 'data_entrada', 'lote', 'peso_entrada', 'valor_compra')
        }),
        ('Custos e Valores', {
            'fields': ('custo_fixo', 'custo_variavel', 'valor_total', 'valor_venda')
        }),
        ('Status', {
            'fields': ('situacao', 'data_saida')
        }),
        ('Histórico', {
            'fields': ('primeiro_peso', 'data_primeiro_peso')
        }),
    )

@admin.register(ClienteLegado)
class ClienteLegadoAdmin(admin.ModelAdmin):
    list_display = ('email', 'nome', 'percentual_desconto', 'ativo', 'data_cadastro')
    list_filter = ('ativo',)
    search_fields = ('email', 'nome')
    ordering = ('nome',)
    fieldsets = (
        (None, {
            'fields': ('email', 'nome', 'ativo')
        }),
        ('Desconto', {
            'fields': ('percentual_desconto',),
            'description': 'Use 100 para dar 100% de desconto na adesão'
        }),
        ('Informações Adicionais', {
            'fields': ('id_eduzz_antigo', 'observacoes'),
            'classes': ('collapse',)
        })
    )
    list_per_page = 50
    save_on_top = True

@admin.register(EduzzTransaction)
class EduzzTransactionAdmin(admin.ModelAdmin):
    list_display = ('email', 'nome', 'plano', 'status', 'valor_original', 'valor_pago', 'data_pagamento')
    list_filter = ('status', 'plano')
    search_fields = ('email', 'nome', 'transaction_id')
    ordering = ('-data_pagamento',)
    readonly_fields = ('transaction_id', 'status', 'data_pagamento', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('email', 'nome', 'plano', 'status')
        }),
        ('Valores', {
            'fields': ('valor_original', 'valor_pago')
        }),
        ('Datas', {
            'fields': ('data_pagamento', 'data_expiracao')
        }),
        ('Informações do Sistema', {
            'fields': ('transaction_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    list_per_page = 50
    save_on_top = True

@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla', 'tipo', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('nome', 'sigla', 'descricao')
    ordering = ('tipo', 'nome')
