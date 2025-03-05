from django.urls import path, include
from . import views
from .views_dashboard import dashboard
from . import views_relatorios
from . import views_estoque
from . import views_nao_operacional
from . import views_fazenda
from . import views_compras
from . import views_vendas
from . import views_parcelas
from . import views_abates
from . import views_dashboard
from . import views_impressao
from . import views_reproducao
from . import views_config
from . import importacao_views
from . import views_account
from . import views_eduzz
from . import views_stripe
from . import auth_supabase

urlpatterns = [
    # Auth
    path('auth/redefinir-senha/<str:token>/', auth_supabase.password_reset_confirm_view, name='password_reset_confirm'),
    path('auth/update-password/', auth_supabase.update_password_view, name='update_password'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views_dashboard.dashboard, name='dashboard'),
    
    # Eduzz Webhooks
    path('api/eduzz/webhook/', views_eduzz.webhook_eduzz, name='webhook_eduzz'),
    path('api/eduzz/test/', views_eduzz.test_eduzz_connection, name='test_eduzz'),
    path('api/eduzz/sync-sales/', views_eduzz.sync_eduzz_sales, name='sync_eduzz_sales'),
    
    # Dashboard
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
    
    # Stripe Endpoints
    path('stripe/checkout/<str:price_id>/', views_stripe.checkout_session, name='stripe_checkout'),
    path('stripe/webhook/', views_stripe.webhook_stripe, name='webhook_stripe'),
    path('stripe/success/', views_stripe.stripe_success, name='stripe_success'),
    path('stripe/cancel/', views_stripe.stripe_cancel, name='stripe_cancel'),
    path('stripe/portal/', views_stripe.portal_stripe, name='stripe_portal'),
    path('stripe/cortesia/', views_stripe.cortesia, name='stripe_cortesia'),
    path('planos-stripe/', views_stripe.planos, name='planos_stripe'),
]
