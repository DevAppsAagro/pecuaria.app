from django.urls import path, include
from . import views
from . import views_relatorios
from . import views_estoque
from . import views_nao_operacional
from . import views_compras
from . import views_vendas
from . import views_parcelas
from . import views_abates
from . import views_dashboard
from . import views_impressao
from . import views_debug  # Importação do módulo de debug
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Rota temporária para debug
    path('financeiro/despesas/debug/', views_debug.DespesasListViewDebug.as_view(), name='despesas_list_debug'),
    
    # Dashboard
    path('', views_dashboard.dashboard, name='dashboard'),
    path('dashboard/atualizar/', views_dashboard.atualizar_dashboard, name='atualizar_dashboard'),
    
    # Página em desenvolvimento
    path('em-desenvolvimento/', views.em_desenvolvimento, name='em_desenvolvimento'),
    
    # Módulos em desenvolvimento
    path('financeiro/', views.em_desenvolvimento, name='financeiro'),
    path('reproducao/', views.em_desenvolvimento, name='reproducao'),
    path('relatorios/', views_relatorios.relatorios_view, name='relatorios_list'),
    path('relatorios/pesagens/', views_relatorios.relatorio_pesagens, name='relatorio_pesagens'),
    path('relatorios/pesagens/imprimir/', views_impressao.imprimir_pesagens, name='imprimir_pesagens'),
    path('relatorios/confinamento/', views_relatorios.relatorio_confinamento, name='relatorio_confinamento'),
    path('relatorios/confinamento/imprimir/', views_impressao.imprimir_confinamento, name='imprimir_confinamento'),
    path('relatorios/dre/', views_relatorios.relatorio_dre, name='relatorio_dre'),
    path('relatorios/dre/atualizar/', views_relatorios.atualizar_dre, name='atualizar_dre'),
    path('api/animais-por-lote/<int:lote_id>/', views_relatorios.animais_por_lote, name='animais_por_lote'),
    
    # Animais
    path('animais/', views.animal_list, name='animal_list'),
    path('animais/novo/', views.animal_create, name='animal-create'),
    path('animais/<int:pk>/', views.animal_detail, name='animal_detail'),
    path('animais/<int:pk>/editar/', views.animal_edit, name='animal_edit'),
    path('animais/<int:pk>/excluir/', views.animal_delete, name='animal_delete'),
    path('animais/importar/', views.animal_import, name='animal_import'),
    path('animais/download-planilha-modelo/', views.download_planilha_modelo, name='download_planilha_modelo'),
    path('animais/<int:animal_pk>/movimentacoes/', views.movimentacao_list, name='movimentacao_list'),
    path('animais/<int:animal_pk>/movimentacoes/nova/', views.movimentacao_create, name='movimentacao_create'),
    path('animal/<int:animal_pk>/movimentacao/criar/', views.movimentacao_create, name='movimentacao_create'),
    path('animal/<int:animal_pk>/movimentacao/historico/', views.movimentacao_list, name='movimentacao_list'),
    path('animais/<int:pk>/imprimir/', views_impressao.imprimir_animal, name='imprimir_animal'),
    
    # Fazendas URLs
    path('fazendas/', views.fazenda_list, name='fazenda_list'),
    path('fazendas/nova/', views.fazenda_create, name='fazenda_create'),
    path('fazendas/<int:pk>/', views.fazenda_detail, name='fazenda_detail'),
    path('fazendas/<int:pk>/editar/', views.fazenda_edit, name='fazenda_edit'),
    path('fazendas/<int:pk>/excluir/', views.fazenda_delete, name='fazenda_delete'),
    
    # Pastos URLs
    path('pastos/', views.pasto_list, name='pasto_list'),
    path('pastos/novo/', views.pasto_create, name='pasto_create'),
    path('pastos/<int:pk>/', views.pasto_detail, name='pasto_detail'),
    path('pastos/<int:pk>/editar/', views.pasto_edit, name='pasto_edit'),
    path('pastos/<int:pk>/excluir/', views.pasto_delete, name='pasto_delete'),
    path('pastos-por-lote/<int:lote_id>/', views.pastos_por_lote, name='pastos_por_lote'),
    
    # Lotes
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/novo/', views.lote_create, name='lote_create'),
    path('lotes/<int:pk>/editar/', views.lote_edit, name='lote_edit'),
    path('lotes/<int:pk>/excluir/', views.lote_delete, name='lote_delete'),
    path('lotes/<int:lote_id>/', views.lote_detail, name='lote_detail'),
    
    # Manejos e Pesagens
    path('manejos/', views.manejo_list, name='manejos'),  
    path('manejos/criar/', views.manejo_create, name='manejo_create'),
    path('manejos/<int:pk>/update/', views.manejo_update, name='manejo_update'),
    path('manejos/<int:pk>/delete/', views.manejo_delete, name='manejo_delete'),
    path('manejos/pesagem/<int:pk>/editar/', views.editar_pesagem, name='editar_pesagem'),
    path('manejos/pesagem/<int:pk>/excluir/', views.excluir_pesagem, name='excluir_pesagem'),
    path('manejos/sanitario/<int:pk>/editar/', views.editar_manejo, name='editar_manejo'),
    path('manejos/sanitario/<int:pk>/excluir/', views.excluir_manejo, name='excluir_manejo'),
    path('pesagens/<int:pk>/update/', views.pesagem_update, name='pesagem_update'),
    path('pesagens/<int:pk>/delete/', views.pesagem_delete, name='pesagem_delete'),
    
    # Máquinas e Benfeitorias
    path('maquinas/', views.maquinas_list, name='maquinas_list'),
    path('maquinas/create/', views.maquina_create, name='maquina_create'),
    path('maquinas/<int:pk>/edit/', views.maquina_edit, name='maquina_edit'),
    path('maquinas/<int:pk>/delete/', views.maquina_delete, name='maquina_delete'),
    path('maquinas/<int:pk>/detail/', views.maquina_detail, name='maquina_detail'),
    # Benfeitorias
    path('benfeitorias/', views.benfeitorias_list, name='benfeitorias_list'),
    path('benfeitorias/criar/', views.benfeitoria_create, name='benfeitoria_create'),
    path('benfeitorias/<int:pk>/', views.benfeitoria_detail, name='benfeitoria_detail'),
    path('benfeitorias/<int:pk>/editar/', views.benfeitoria_edit, name='benfeitoria_edit'),
    path('benfeitorias/<int:pk>/excluir/', views.benfeitoria_delete, name='benfeitoria_delete'),
    
    # Estoque
    path('estoque/', views_estoque.estoque_list, name='estoque_list'),
    path('estoque/insumo/novo/', views_estoque.insumo_create, name='insumo_create'),
    path('estoque/insumo/<int:pk>/editar/', views_estoque.insumo_edit, name='insumo_edit'),
    path('estoque/insumo/<int:pk>/excluir/', views_estoque.insumo_delete, name='insumo_delete'),
    path('estoque/entrada/', views_estoque.entrada_list, name='entrada_list'),
    path('estoque/entrada/nova/', views_estoque.entrada_estoque, name='entrada_estoque'),
    path('estoque/entrada/<int:pk>/editar/', views_estoque.entrada_edit, name='entrada_edit'),
    path('estoque/entrada/<int:pk>/excluir/', views_estoque.entrada_delete, name='entrada_delete'),
    path('estoque/entrada/<int:pk>/', views_estoque.entrada_detail, name='entrada_detail'),
    path('estoque/saida/', views_estoque.saida_list, name='saida_list'),
    path('estoque/saida/novo/', views_estoque.saida_estoque, name='saida_estoque'),
    path('estoque/saida/<int:pk>/', views_estoque.saida_detail, name='saida_detail'),
    path('estoque/saida/<int:pk>/editar/', views_estoque.saida_edit, name='saida_edit'),
    path('estoque/saida/<int:pk>/excluir/', views_estoque.saida_delete, name='saida_delete'),
    path('estoque/saida-nutricao/', views_estoque.saida_nutricao_list, name='saida_nutricao_list'),
    path('estoque/saida-nutricao/novo/', views_estoque.saida_nutricao_estoque, name='saida_nutricao_estoque'),
    path('estoque/saida-nutricao/<int:pk>/', views_estoque.saida_nutricao_detail, name='saida_nutricao_detail'),
    path('estoque/saida-nutricao/<int:pk>/editar/', views_estoque.saida_nutricao_edit, name='saida_nutricao_edit'),
    path('estoque/saida-nutricao/<int:pk>/excluir/', views_estoque.saida_nutricao_delete, name='saida_nutricao_delete'),
    path('get-subcategorias/', views_estoque.get_subcategorias, name='get_subcategorias'),
    path('get-insumo-info/', views_estoque.get_insumo_info, name='get_insumo_info'),
    path('get-insumos/', views.get_insumos, name='get_insumos'),
    path('get-pasto-lote/', views_estoque.get_pasto_lote, name='get_pasto_lote'),
    
    # Financeiro
    path('financeiro/despesas/', views.DespesasListView.as_view(), name='despesas_list'),
    path('financeiro/despesas/print/', views_impressao.despesas_print, name='despesas_print'),
    path('financeiro/despesa/create/', views.DespesaCreateView.as_view(), name='despesa_create'),
    path('financeiro/despesa/<int:pk>/', views.despesa_detail, name='despesa_detail'),
    path('financeiro/despesa/<int:pk>/update/', views.DespesaUpdateView.as_view(), name='despesa_update'),
    path('financeiro/despesa/<int:pk>/delete/', views.DespesaDeleteView.as_view(), name='despesa_delete'),
    path('api/financeiro/despesa/<int:pk>/pagar/', views.pagar_despesa, name='pagar_despesa'),
    path('api/financeiro/parcela/<int:pk>/pagar/', views.pagar_parcela, name='pagar_parcela'),
    path('api/financeiro/despesas/get_destinos/', views.get_destinos, name='get_destinos'),
    path('api/financeiro/despesas/get_subcategorias/', views.get_subcategorias, name='get_subcategorias'),
    path('api/financeiro/despesas/get_unidades_medida/', views.get_unidades_medida, name='get_unidades_medida'),
    
    # Vendas URLs
    path('financeiro/vendas/', views_vendas.lista_vendas, name='vendas_list'),
    path('financeiro/vendas/nova/', views_vendas.criar_venda, name='vendas_criar'),
    path('financeiro/vendas/<int:pk>/', views_vendas.detalhe_venda, name='vendas_detalhe'),
    path('financeiro/vendas/<int:pk>/editar/', views_vendas.editar_venda, name='vendas_editar'),
    path('financeiro/vendas/<int:pk>/excluir/', views_vendas.excluir_venda, name='vendas_excluir'),
    path('api/animais/<int:pk>/peso/', views_vendas.get_peso_atual, name='get_peso_atual'),
    path('financeiro/vendas/parcelas/<int:parcela_id>/pagar/', views_vendas.registrar_pagamento_venda, name='registrar_pagamento_venda'),
    path('financeiro/vendas/parcelas/<int:parcela_id>/historico/', views_vendas.historico_pagamentos_venda, name='historico_pagamentos_venda'),
    
    # Abates URLs
    path('financeiro/abates/', views_abates.lista_abates, name='abates_list'),
    path('financeiro/abates/novo/', views_abates.criar_abate, name='abates_criar'),
    path('financeiro/abates/<int:pk>/', views_abates.detalhe_abate, name='abates_detalhe'),
    path('financeiro/abates/<int:pk>/editar/', views_abates.editar_abate, name='abates_editar'),
    path('financeiro/abates/<int:pk>/excluir/', views_abates.excluir_abate, name='abates_excluir'),
    path('financeiro/abates/parcelas/<int:parcela_id>/pagar/', views_abates.registrar_pagamento_abate, name='registrar_pagamento_abate'),
    path('financeiro/abates/parcelas/<int:parcela_id>/historico/', views_abates.historico_pagamentos_abate, name='historico_pagamentos_abate'),
    path('api/animal/peso/', views_abates.get_peso_atual_json, name='animal_peso_api'),
    
    # Compras
    path('financeiro/compras/', views_compras.compras_list, name='compras_list'),
    path('financeiro/compras/nova/', views_compras.criar_compra, name='compras_criar'),
    path('financeiro/compras/<int:pk>/editar/', views_compras.editar_compra, name='compras_editar'),
    path('financeiro/compras/<int:pk>/excluir/', views_compras.excluir_compra, name='compras_excluir'),
    path('financeiro/compras/<int:pk>/detalhe/', views_compras.detalhe_compra, name='compras_detalhe'),
    path('financeiro/compras/imprimir/', views_impressao.imprimir_compras, name='compras_print'),
    
    # Parcelas URLs
    path('financeiro/parcelas/<int:parcela_id>/pagar/', views_parcelas.registrar_pagamento, name='registrar_pagamento'),
    path('financeiro/parcelas/<int:parcela_id>/historico/', views_parcelas.historico_pagamentos, name='historico_pagamentos'),
    
    # Movimentações Não Operacionais
    path('nao-operacional/', views_nao_operacional.lista_nao_operacional, name='lista_nao_operacional'),
    path('nao-operacional/criar/', views_nao_operacional.criar_nao_operacional, name='criar_nao_operacional'),
    path('nao-operacional/<int:pk>/editar/', views_nao_operacional.editar_nao_operacional, name='editar_nao_operacional'),
    path('nao-operacional/<int:pk>/excluir/', views_nao_operacional.excluir_nao_operacional, name='excluir_nao_operacional'),
    
    # Contatos
    path('contatos/', views.ContatoListView.as_view(), name='contatos_list'),
    path('contatos/novo/', views.ContatoCreateView.as_view(), name='contato_create'),
    path('contatos/<int:pk>/editar/', views.ContatoUpdateView.as_view(), name='contato_update'),
    path('contatos/<int:pk>/excluir/', views.ContatoDeleteView.as_view(), name='contato_delete'),
    
    # URLs para Contas Bancárias
    path('financeiro/contas-bancarias/', views.ContaBancariaListView.as_view(), name='contas_bancarias_list'),
    path('financeiro/contas-bancarias/criar/', views.ContaBancariaCreateView.as_view(), name='contas_bancarias_create'),
    path('financeiro/contas-bancarias/<int:pk>/editar/', views.ContaBancariaUpdateView.as_view(), name='contas_bancarias_update'),
    path('financeiro/contas-bancarias/<int:pk>/excluir/', views.ContaBancariaDeleteView.as_view(), name='contas_bancarias_delete'),
    path('financeiro/extrato-bancario/', views.ExtratoBancarioListView.as_view(), name='extrato_bancario_list'),

    # APIs
    path('api/get-cidade-coordenadas/', views.get_cidade_coordenadas, name='get_cidade_coordenadas'),
    path('api/buscar_animal/<str:brinco>/', views.buscar_animal, name='buscar_animal'),
    path('api/pastos-por-lote/<int:lote_id>/', views.pastos_por_lote, name='pastos_por_lote'),
    path('api/financeiro/categorias/<int:categoria_id>/subcategorias/', views.get_subcategorias, name='get_subcategorias'),
    path('api/financeiro/destinos/', views.get_destinos, name='get_destinos'),
    path('api/financeiro/unidades-medida/', views.get_unidades_medida, name='get_unidades_medida'),
    path('api/animais/<int:pk>/peso/', views_abates.get_peso_atual_json, name='api_peso_animal'),
    
    # Configurações - Raças
    path('configuracoes/racas/', views.raca_list, name='raca_list'),
    path('configuracoes/racas/nova/', views.raca_create, name='raca_create'),
    path('configuracoes/racas/<int:pk>/editar/', views.raca_edit, name='raca_edit'),
    path('configuracoes/racas/<int:pk>/excluir/', views.raca_delete, name='raca_delete'),
    
    # Configurações - Finalidades de Lote
    path('configuracoes/finalidades-lote/', views.finalidade_lote_list, name='finalidade_lote_list'),
    path('configuracoes/finalidades-lote/nova/', views.finalidade_lote_create, name='finalidade_lote_create'),
    path('configuracoes/finalidades-lote/<int:pk>/editar/', views.finalidade_lote_edit, name='finalidade_lote_edit'),
    path('configuracoes/finalidades-lote/<int:pk>/excluir/', views.finalidade_lote_delete, name='finalidade_lote_delete'),
    
    # Configurações - Categorias de Animal
    path('configuracoes/categorias-animal/', views.categoria_animal_list, name='categoria_animal_list'),
    path('configuracoes/categorias-animal/nova/', views.categoria_animal_create, name='categoria_animal_create'),
    path('configuracoes/categorias-animal/<int:pk>/editar/', views.categoria_animal_edit, name='categoria_animal_edit'),
    path('configuracoes/categorias-animal/<int:pk>/excluir/', views.categoria_animal_delete, name='categoria_animal_delete'),
    
    # Configurações - Unidades de Medida
    path('configuracoes/unidades-medida/', views.unidade_medida_list, name='unidade-medida-list'),
    path('configuracoes/unidades-medida/nova/', views.unidade_medida_create, name='unidade-medida-create'),
    path('configuracoes/unidades-medida/<int:pk>/editar/', views.unidade_medida_edit, name='unidade-medida-update'),
    path('configuracoes/unidades-medida/<int:pk>/excluir/', views.unidade_medida_delete, name='unidade-medida-delete'),
    
    # Configurações - Motivos de Morte
    path('configuracoes/motivos-morte/', views.motivo_morte_list, name='motivo-morte-list'),
    path('configuracoes/motivos-morte/novo/', views.motivo_morte_create, name='motivo-morte-create'),
    path('configuracoes/motivos-morte/<int:pk>/editar/', views.motivo_morte_edit, name='motivo-morte-update'),
    path('configuracoes/motivos-morte/<int:pk>/excluir/', views.motivo_morte_delete, name='motivo-morte-delete'),
    
    # Configurações - Variedade de Capim
    path('configuracoes/variedade-capim/', views.variedade_capim_list, name='variedade-capim-list'),
    path('configuracoes/variedade-capim/novo/', views.variedade_capim_create, name='variedade-capim-create'),
    path('configuracoes/variedade-capim/<int:pk>/editar/', views.variedade_capim_edit, name='variedade-capim-edit'),
    path('configuracoes/variedade-capim/<int:pk>/excluir/', views.variedade_capim_delete, name='variedade-capim-delete'),
    
    # Configurações - Categorias de Custos
    path('configuracoes/categorias-custo/', views.categoria_custo_list, name='categoria-custo-list'),
    path('configuracoes/categorias-custo/novo/', views.categoria_custo_create, name='categoria-custo-create'),
    path('configuracoes/categorias-custo/<int:pk>/editar/', views.categoria_custo_edit, name='categoria-custo-edit'),
    path('configuracoes/categorias-custo/<int:pk>/excluir/', views.categoria_custo_delete, name='categoria-custo-delete'),
    
    # Configurações - Subcategorias de Custos
    path('configuracoes/subcategorias-custo/', views.subcategoria_custo_list, name='subcategoria-custo-list'),
    path('configuracoes/subcategorias-custo/novo/', views.subcategoria_custo_create, name='subcategoria-custo-create'),
    path('configuracoes/subcategorias-custo/<int:pk>/editar/', views.subcategoria_custo_edit, name='subcategoria-custo-edit'),
    path('configuracoes/subcategorias-custo/<int:pk>/excluir/', views.subcategoria_custo_delete, name='subcategoria-custo-delete'),
    
    # Bulk Actions
    path('animais/bulk-action/', views.bulk_action, name='bulk_action'),
    path('animais/bulk-edit/', views.bulk_edit, name='bulk_edit'),
    path('animais/bulk-move/', views.bulk_move, name='bulk_move'),
    path('animais/bulk-move-lot/', views.bulk_move_lot, name='bulk_move_lot'),
    
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('aguardando-pagamento/', views.awaiting_payment, name='awaiting_payment'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
]
