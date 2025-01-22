from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from .models import Animal, Pesagem, ManejoSanitario, MovimentacaoAnimal, RateioCusto
from .models_compras import CompraAnimal
from .models_vendas import VendaAnimal
from .models_abates import AbateAnimal

@login_required
def imprimir_animal(request, pk):
    animal = get_object_or_404(Animal, pk=pk, usuario=request.user)
    
    # Busca informações de abate e venda
    abate_animal = AbateAnimal.objects.filter(animal=animal).first()
    venda = VendaAnimal.objects.filter(animal=animal).first()
    
    # Calcula dias ativos - usa data de saída se existir, senão usa hoje
    data_entrada = animal.data_entrada
    if abate_animal:
        data_final = abate_animal.abate.data
    elif venda:
        data_final = venda.data
    else:
        data_final = timezone.now().date()
    
    dias_ativos = (data_final - data_entrada).days if data_entrada else 0
    
    # Pega a última pesagem
    ultima_pesagem = animal.pesagens.order_by('-data').first()
    
    # Calcula peso atual e @ atual
    peso_atual = ultima_pesagem.peso if ultima_pesagem else None
    arroba_atual = None
    if peso_atual:
        # Se tem abate, usa o rendimento do abate, senão usa 50%
        rendimento = Decimal(str(abate_animal.rendimento)) / Decimal('100') if abate_animal else Decimal('0.5')
        arroba_atual = (Decimal(str(peso_atual)) * rendimento / Decimal('15'))
    
    # Calcula @ de entrada (sempre usa 50% de rendimento na entrada)
    peso_entrada = Decimal(str(animal.peso_entrada)) if animal.peso_entrada else 0
    arroba_entrada = (peso_entrada * Decimal('0.5') / Decimal('15'))

    # Calcula ganho em @
    ganho_arroba = Decimal(str(arroba_atual - arroba_entrada)) if arroba_atual else None

    # Calcula o GMD (Ganho Médio Diário)
    gmd = 0
    ganho_peso = 0
    if peso_atual and animal.peso_entrada and dias_ativos > 0:
        ganho_peso = peso_atual - animal.peso_entrada
        gmd = round(ganho_peso / dias_ativos, 3)

    # Calcula custos
    rateios = RateioCusto.objects.filter(animal=animal)
    custos_fixos_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'fixo')
    custos_variaveis_totais = sum(rateio.valor for rateio in rateios if rateio.item_despesa.categoria.tipo == 'variavel')
    custos_variaveis_totais += animal.custo_variavel or 0
    custos_total = Decimal(str(custos_fixos_totais)) + Decimal(str(custos_variaveis_totais))

    # Calcula custos por kg e por @
    custo_por_kg = 0
    custo_por_arroba = 0
    
    if animal.peso_entrada is not None and ultima_pesagem and ganho_arroba and ganho_arroba > 0:
        ganho_total = Decimal(str(peso_atual)) - Decimal(str(animal.peso_entrada))
        
        if custos_total > 0:
            # Calcula custo por kg (custo total / kg produzido)
            custo_por_kg = float(custos_total / ganho_total)
            # Calcula custo por @ (custo total / @ produzida)
            custo_por_arroba = float(custos_total / ganho_arroba)

    # Calcula custos diários
    if dias_ativos > 0:
        custo_diario = custos_total / Decimal(str(dias_ativos))
        custo_variavel_diario = Decimal(str(custos_variaveis_totais)) / dias_ativos
        custo_fixo_diario = Decimal(str(custos_fixos_totais)) / dias_ativos
    else:
        custo_diario = Decimal('0')
        custo_variavel_diario = Decimal('0')
        custo_fixo_diario = Decimal('0')

    # Informações de abate/venda
    valor_entrada = animal.valor_compra or 0
    
    # Busca informações de compra
    compra_animal = CompraAnimal.objects.filter(animal=animal).first()
    
    peso_final = 0
    valor_saida = 0
    arrobas_final = 0
    lucro = 0

    # Busca informações de abate
    if abate_animal:
        peso_final = abate_animal.peso_vivo
        valor_saida = abate_animal.valor_total
        # Calcula arrobas considerando o rendimento de carcaça
        rendimento_carcaca = Decimal(str(abate_animal.rendimento)) / Decimal('100')
        arrobas_final = (peso_final * rendimento_carcaca / Decimal('15')) if peso_final else 0
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    elif venda:
        peso_final = venda.peso
        valor_saida = venda.valor_total
        arrobas_final = peso_final / Decimal('30')  # Venda usa rendimento padrão de 50%
        lucro = valor_saida - valor_entrada - custos_total if valor_saida else 0
    else:
        peso_final = ultima_pesagem.peso if ultima_pesagem else peso_atual
        arrobas_final = peso_final / Decimal('30') if peso_final else 0

    # Buscar históricos
    pesagens = Pesagem.objects.filter(animal=animal).order_by('-data')
    manejos = ManejoSanitario.objects.filter(animal=animal).order_by('-data')
    movimentacoes = MovimentacaoAnimal.objects.filter(animal=animal).order_by('-data_movimentacao')
    
    # Informações do cabeçalho
    cabecalho = {
        'empresa': 'FAZENDA MODELO LTDA',
        'cnpj': '12.345.678/0001-90',
        'endereco': 'Rodovia BR 101, Km 123',
        'cidade_uf': 'Cidade Alta - MT',
        'telefone': '(11) 1234-5678',
        'email': 'contato@fazendamodelo.com.br'
    }
    
    # Informações do rodapé
    rodape = {
        'responsavel_tecnico': 'Dr. João Silva',
        'crmv': 'CRMV-MT 12345',
        'sistema': 'Sistema de Gestão Pecuária v1.0'
    }
    
    context = {
        'animal': animal,
        'dias_ativos': dias_ativos,
        'compra': compra_animal,
        'venda': venda,
        'abate': abate_animal,
        'arrobas_final': arrobas_final,
        'pesagens': pesagens,
        'manejos': manejos,
        'movimentacoes': movimentacoes,
        'peso_atual': peso_atual,
        'arroba_atual': arroba_atual,
        'arroba_entrada': arroba_entrada,
        'ganho_arroba': ganho_arroba,
        'custo_total': custos_total,
        'custos_fixos_totais': custos_fixos_totais,
        'custos_variaveis_totais': custos_variaveis_totais,
        'custo_por_kg': custo_por_kg,
        'custo_por_arroba': custo_por_arroba,
        'custo_diario': custo_diario,
        'custo_fixo_diario': custo_fixo_diario,
        'custo_variavel_diario': custo_variavel_diario,
        'lucro': lucro,
        'gmd': gmd,
        'cabecalho': cabecalho,
        'rodape': rodape,
    }
    
    return render(request, 'impressao/animal_detail_print.html', context)
