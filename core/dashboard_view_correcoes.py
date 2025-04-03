"""
Correções para o arquivo views_dashboard_simples.py

1. Correção para o erro 'Despesa' object has no attribute 'valor_pago'
   - Substituir todas as ocorrências de despesa.valor_pago por despesa.valor_final()

2. Correção para o erro Cannot resolve keyword 'pago' into field
   - Substituir filtros como pago=False por status='PENDENTE'
   - Substituir filtros como pago=True por status='PAGO'

3. Correção para o erro Cannot resolve keyword 'data_abate' into field
   - Substituir todas as ocorrências de data_abate por data

4. Correção para pastos com benfeitorias não aparecerem
   - Garantir que a consulta de pastos inclua todos os tipos de pastos

5. Correção para os gráficos não aparecerem
   - Verificar se os dados estão sendo passados corretamente para o template
   - Garantir que o JavaScript está inicializando os gráficos corretamente
"""

# Exemplo de correção para o erro 'valor_pago'
# Antes:
# total_saidas += float(despesa.valor_pago)
# Depois:
total_saidas += float(despesa.valor_final())

# Exemplo de correção para o erro 'pago'
# Antes:
# despesas_pendentes = Despesa.objects.filter(pago=False, usuario=request.user)
# Depois:
despesas_pendentes = Despesa.objects.filter(status='PENDENTE', usuario=request.user)

# Exemplo de correção para o erro 'data_abate'
# Antes:
# abates = Abate.objects.filter(data_abate__gte=data_inicio, data_abate__lte=data_fim)
# Depois:
abates = Abate.objects.filter(data__gte=data_inicio, data__lte=data_fim)

# Correção para pastos com benfeitorias
# Antes:
# pastos_filtrados = Pasto.objects.filter(fazenda__usuario=request.user)
# Depois (garantir que todos os pastos sejam incluídos):
pastos_filtrados = Pasto.objects.filter(fazenda__usuario=request.user)
# Verificar se há algum filtro adicional que esteja excluindo pastos com benfeitorias

# Correção para os gráficos não aparecerem
# No JavaScript, garantir que os gráficos sejam inicializados após os dados estarem disponíveis:
"""
// Inicializar gráficos quando os dados estiverem prontos
function inicializarGraficos() {
    // Gráfico de distribuição por lotes
    const ctxLotes = document.getElementById('graficoLotes').getContext('2d');
    if (graficoLotes) {
        graficoLotes.destroy();
    }
    graficoLotes = new Chart(ctxLotes, {
        type: 'pie',
        data: {
            labels: dadosLotes.map(item => item.nome),
            datasets: [{
                data: dadosLotes.map(item => item.quantidade),
                backgroundColor: dadosLotes.map(item => item.cor),
                hoverBorderColor: '#ffffff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12
                    }
                }
            }
        }
    });

    // Gráfico de distribuição por pastos
    const ctxPastos = document.getElementById('graficoPastos').getContext('2d');
    if (graficoPastos) {
        graficoPastos.destroy();
    }
    graficoPastos = new Chart(ctxPastos, {
        type: 'pie',
        data: {
            labels: dadosPastos.map(item => item.nome),
            datasets: [{
                data: dadosPastos.map(item => item.quantidade),
                backgroundColor: dadosPastos.map(item => item.cor),
                hoverBorderColor: '#ffffff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12
                    }
                }
            }
        }
    });
}
"""
