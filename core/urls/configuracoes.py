from django.urls import path
from core.views.configuracoes import *

urlpatterns = [
    # Raças
    path('configuracoes/racas/', RacaListView.as_view(), name='raca_list'),
    
    # Finalidades de Lote
    path('configuracoes/finalidades-lote/', FinalidadeLoteListView.as_view(), name='finalidade_lote_list'),
    
    # Categorias de Animais
    path('configuracoes/categorias-animais/', CategoriaAnimalListView.as_view(), name='categoria_animal_list'),
    
    # Unidades de Medida
    path('configuracoes/unidades-medida/', UnidadeMedidaListView.as_view(), name='unidade_medida_list'),
    
    # Motivos de Morte
    path('configuracoes/motivos-morte/', MotivoMorteListView.as_view(), name='motivo_morte_list'),
    
    # Categorias de Custos
    path('configuracoes/categorias-custos/', CategoriaCustoListView.as_view(), name='categoria_custo_list'),
    
    # Variedades de Capim
    path('configuracoes/variedades-capim/', VariedadeCapimListView.as_view(), name='variedade_capim_list'),
]
