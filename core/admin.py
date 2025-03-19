from django.contrib import admin
from .models import Fazenda, Animal, UnidadeMedida

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

@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla', 'tipo', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('nome', 'sigla', 'descricao')
    ordering = ('tipo', 'nome')
