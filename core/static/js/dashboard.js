/**
 * Dashboard.js - Script para o dashboard da aplicação Pecuaria.app
 * Desenvolvido por LWL Solutions
 */

// Variáveis globais
let map;
let fazendaId;
let marcadoresPastos = [];
let overlayLayers = [];

/**
 * Inicialização após carregamento do DOM
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando dashboard...');
    
    // Obter o ID da fazenda selecionada
    const select = document.getElementById('fazenda-select');
    if (select) {
        fazendaId = select.value;
        
        // Event listener para mudança na seleção da fazenda
        select.addEventListener('change', function() {
            fazendaId = this.value;
            console.log('Fazenda selecionada:', fazendaId);
            
            // Recarregar dashboard com a nova fazenda
            carregarDashboard();
        });
    }
    
    // Inicializar o mapa
    initMapa();
    
    // Inicializar os contadores de KPI
    initKPICounters();
    
    // Inicializar os gráficos
    initGraficos();
});

/**
 * Carrega todos os elementos do dashboard
 */
function carregarDashboard() {
    // Limpar marcadores e layers existentes
    if (map) {
        limparMapa();
        carregarDadosMapa(map);
    }
    
    // Atualizar KPIs e gráficos
    initKPICounters();
    initGraficos();
}

/**
 * Inicializa os contadores de KPI
 */
function initKPICounters() {
    console.log('Inicializando KPIs...');
    
    fetch(`/dashboard/atualizar/?fazenda=${fazendaId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao buscar dados para KPIs');
            }
            return response.json();
        })
        .then(data => {
            console.log('Dados recebidos para KPIs:', data);
            
            // Criar objeto com os indicadores
            const indicadores = {
                total_animais: data.total_animais || 0,
                total_bezerros: data.total_bezerros || 0,
                total_femeas: data.total_femeas || 0,
                peso_medio: data.peso_medio || 0,
                total_receitas: data.total_receitas || 0,
                lucro_total: data.lucro_total || 0
            };
            
            // Atualizar os KPIs na interface
            atualizarKPIs(indicadores);
        })
        .catch(error => {
            console.error('Erro ao inicializar KPIs:', error);
            mostrarNotificacao('Erro ao carregar indicadores. Por favor, recarregue a página.', 'erro');
        });
}

/**
 * Inicializa os gráficos
 */
function initGraficos() {
    console.log('Inicializando gráficos...');
    
    fetch(`/dashboard/atualizar/?fazenda=${fazendaId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao buscar dados para gráficos');
            }
            return response.json();
        })
        .then(data => {
            console.log('Dados recebidos para gráficos:', data);
            processarDadosGraficos(data);
        })
        .catch(error => {
            console.error('Erro ao inicializar gráficos:', error);
            mostrarNotificacao('Erro ao carregar gráficos. Por favor, recarregue a página.', 'erro');
        });
}

/**
 * Inicializa os contadores de KPI na dashboard
 */
function initKPICounters() {
    const fazendaId = document.getElementById('fazenda-select')?.value;
    console.log('Inicializando contadores KPI para fazenda:', fazendaId);
    
    fetch(`/dashboard/atualizar/?fazenda=${fazendaId}`)
        .then(response => response.json())
        .then(data => {
            console.log('Dados de KPI recebidos:', data);
            atualizarKPIs(data.indicadores);
        })
        .catch(error => {
            console.error('Erro ao carregar dados de KPI:', error);
            mostrarNotificacao('Erro ao carregar indicadores', 'erro');
        });
}

/**
 * Atualiza os KPIs na interface
 */
function atualizarKPIs(indicadores) {
    console.log('Atualizando KPIs com dados:', indicadores);
    
    // Verificar se temos os dados necessários
    if (!indicadores) {
        console.warn('Dados de indicadores não disponíveis');
        return;
    }
    
    // Encontrar todos os elementos counter-value
    const counters = document.querySelectorAll('.counter-value');
    
    // Atualizar cada contador com animação
    counters.forEach(counter => {
        // Obter o valor alvo do data-target
        const originalTarget = parseInt(counter.getAttribute('data-target') || '0');
        
        // Determinar qual valor usar
        let target = originalTarget;
        
        // Atualizar data-target com o valor atual da API (se disponível)
        if (counter.closest('.kpi-primary')) {
            // Card de Total de Animais
            if (indicadores.total_animais) {
                target = indicadores.total_animais;
                counter.setAttribute('data-target', target);
            }
        } else if (counter.closest('.kpi-success')) {
            // Card de Bezerros
            if (indicadores.total_bezerros) {
                target = indicadores.total_bezerros;
                counter.setAttribute('data-target', target);
            }
        } else if (counter.closest('.kpi-info')) {
            // Card de Fêmeas
            if (indicadores.total_femeas) {
                target = indicadores.total_femeas;
                counter.setAttribute('data-target', target);
            }
        } else if (counter.closest('.kpi-warning')) {
            // Card de Peso Médio
            if (indicadores.peso_medio) {
                target = indicadores.peso_medio;
                counter.setAttribute('data-target', target);
            }
        } else if (counter.closest('.kpi-danger')) {
            // Card de Receitas
            if (indicadores.total_receitas) {
                target = indicadores.total_receitas;
                counter.setAttribute('data-target', target);
            }
        } else if (counter.closest('.kpi-secondary')) {
            // Card de Lucro
            if (indicadores.lucro_total) {
                target = indicadores.lucro_total;
                counter.setAttribute('data-target', target);
            }
        }
        
        // Animação do contador
        const duration = 1500; // duração da animação em ms
        const startTime = performance.now();
        
        function updateCounter(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // easing cúbico
            const currentValue = Math.floor(easeProgress * target);
            
            counter.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target.toLocaleString();
            }
        }
        
        requestAnimationFrame(updateCounter);
    });
}

/**
 * Processa os dados recebidos para os gráficos
 */
function processarDadosGraficos(data) {
    console.log('Processando dados para gráficos:', data);
    
    // Limpar qualquer gráfico existente
    limparGraficosExistentes();
    
    // Criar os gráficos com os dados
    criarGraficoEvolucao(data);
    criarGraficoFinanceiro(data);
    criarGraficoCategorias(data);
    criarGraficoDesempenhoLotes(data);
}

/**
 * Limpa gráficos existentes para evitar duplicação
 */
function limparGraficosExistentes() {
    const graficos = ['grafico-evolucao', 'grafico-financeiro', 'grafico-categorias', 'grafico-desempenho-lotes'];
    
    graficos.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.chart) {
            el.chart.destroy();
        }
    });
}

/**
 * Cria o gráfico de evolução do rebanho
 */
function criarGraficoEvolucao(dados) {
    const ctx = document.getElementById('grafico-evolucao');
    if (!ctx) {
        console.warn('Elemento canvas para gráfico de evolução não encontrado');
        return;
    }
    
    // Dados do gráfico
    const labels = dados.evolucao_rebanho ? dados.evolucao_rebanho.map(item => item.mes) : 
                 ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'];
    
    const quantidades = dados.evolucao_rebanho ? dados.evolucao_rebanho.map(item => item.quantidade) : 
                      [500, 520, 540, 560, 580, 600];
    
    const pesos = dados.evolucao_rebanho ? dados.evolucao_rebanho.map(item => item.peso_medio) : 
                [380, 395, 410, 430, 445, 460];
    
    // Criar o gráfico
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Quantidade',
                    data: quantidades,
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.05)',
                    pointBackgroundColor: '#4e73df',
                    tension: 0.4,
                    yAxisID: 'y',
                    fill: true
                },
                {
                    label: 'Peso Médio (kg)',
                    data: pesos,
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.05)',
                    pointBackgroundColor: '#1cc88a',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 10
                        },
                        boxWidth: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Quantidade',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Peso (kg)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
    
    // Armazenar referência do gráfico para poder destruí-lo depois
    ctx.chart = chart;
}

/**
 * Cria o gráfico financeiro
 */
function criarGraficoFinanceiro(dados) {
    const ctx = document.getElementById('grafico-financeiro');
    if (!ctx) {
        console.warn('Elemento canvas para gráfico financeiro não encontrado');
        return;
    }
    
    // Dados do gráfico
    const labels = dados.financeiro ? dados.financeiro.map(item => item.mes) : 
                 ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'];
    
    const receitas = dados.financeiro ? dados.financeiro.map(item => item.receitas) : 
                   [120000, 135000, 145000, 140000, 160000, 170000];
    
    const despesas = dados.financeiro ? dados.financeiro.map(item => item.despesas) : 
                   [90000, 95000, 100000, 105000, 110000, 115000];
    
    const lucro = dados.financeiro ? dados.financeiro.map(item => item.lucro) : 
                [30000, 40000, 45000, 35000, 50000, 55000];
    
    // Criar o gráfico
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'line',
                    label: 'Receitas',
                    data: receitas,
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.05)',
                    pointBackgroundColor: '#1cc88a',
                    tension: 0.4,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    type: 'line',
                    label: 'Despesas',
                    data: despesas,
                    borderColor: '#e74a3b',
                    backgroundColor: 'rgba(231, 74, 59, 0.05)',
                    pointBackgroundColor: '#e74a3b',
                    tension: 0.4,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    type: 'bar',
                    label: 'Lucro',
                    data: lucro,
                    backgroundColor: '#4e73df',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 10
                        },
                        boxWidth: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: false,
                        text: 'Receitas e Despesas (R$)'
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: false,
                        text: 'Lucro (R$)'
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
    
    // Armazenar referência do gráfico para poder destruí-lo depois
    ctx.chart = chart;
}

/**
 * Cria o gráfico de distribuição por categorias
 */
function criarGraficoCategorias(dados) {
    const ctx = document.getElementById('grafico-categorias');
    if (!ctx) {
        console.warn('Elemento canvas para gráfico de categorias não encontrado');
        return;
    }
    
    // Dados do gráfico
    const categorias = dados.categorias ? dados.categorias.map(item => item.categoria) : 
                     ['Bezerros', 'Novilhas', 'Bois', 'Vacas'];
    
    const quantidades = dados.categorias ? dados.categorias.map(item => item.quantidade) : 
                      [150, 125, 100, 125];
    
    // Cores para as categorias
    const cores = ['#1cc88a', '#4e73df', '#36b9cc', '#f6c23e', '#e74a3b', '#858796'];
    
    // Criar o gráfico
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categorias,
            datasets: [{
                data: quantidades,
                backgroundColor: cores.slice(0, categorias.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: {
                            size: 10
                        },
                        boxWidth: 12
                    }
                }
            },
            cutout: '60%'
        }
    });
    
    // Armazenar referência do gráfico para poder destruí-lo depois
    ctx.chart = chart;
}

/**
 * Cria o gráfico de desempenho por lotes
 */
function criarGraficoDesempenhoLotes(dados) {
    const ctx = document.getElementById('grafico-desempenho-lotes');
    if (!ctx) {
        console.warn('Elemento canvas para gráfico de desempenho por lotes não encontrado');
        return;
    }
    
    // Dados do gráfico
    const lotes = dados.desempenho_lotes ? dados.desempenho_lotes.map(item => 'Lote ' + item.lote) : 
                ['Lote A', 'Lote B', 'Lote C', 'Lote D', 'Lote E'];
    
    const gmd = dados.desempenho_lotes ? dados.desempenho_lotes.map(item => item.gmd) : 
             [0.8, 0.9, 0.7, 1.0, 0.85];
    
    // Criar o gráfico
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: lotes,
            datasets: [{
                label: 'GMD (kg/dia)',
                data: gmd,
                backgroundColor: '#4e73df',
                borderColor: '#3a5ccc',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `GMD: ${context.raw.toFixed(2)} kg/dia`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'GMD (kg/dia)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 10
                        },
                        callback: function(value) {
                            return value.toFixed(1);
                        }
                    }
                }
            }
        }
    });
    
    // Armazenar referência do gráfico para poder destruí-lo depois
    ctx.chart = chart;
}

/**
 * Inicializa o mapa
 */
function initMapa() {
    console.log('Inicializando mapa da fazenda...');
    
    // Obter o elemento do mapa
    const mapElement = document.getElementById('mapa-fazenda');
    if (!mapElement) {
        console.error('Elemento do mapa não encontrado');
        return;
    }
    
    // Criar mapa
    map = L.map('mapa-fazenda', {
        center: [-16.6782, -49.2553], // Coordenadas iniciais (Goiânia)
        zoom: 13,
        attributionControl: false
    });
    
    // Adicionar camada base do Google Maps (híbrido)
    L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        attribution: '&copy; Google Maps'
    }).addTo(map);
    
    // Adicionar escala
    L.control.scale({
        imperial: false,
        maxWidth: 200
    }).addTo(map);
    
    // Carregar dados do mapa
    carregarDadosMapa(map);
}

/**
 * Carrega os dados do mapa
 */
function carregarDadosMapa(map) {
    console.log('Carregando dados do mapa para a fazenda ID:', fazendaId);
    
    fetch(`/dashboard/atualizar/?fazenda=${fazendaId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao buscar dados para o mapa');
            }
            return response.json();
        })
        .then(data => {
            console.log('Dados recebidos para o mapa:', data);
            
            // Processar dados dos pastos
            if (data.pastos && data.pastos.length > 0) {
                processarPastos(map, data.pastos);
            } else {
                console.warn('Dados dos pastos não disponíveis ou vazios');
            }
            
            // Processar dados das benfeitorias
            if (data.benfeitorias && data.benfeitorias.length > 0) {
                processarBenfeitorias(map, data.benfeitorias);
            } else {
                console.warn('Dados das benfeitorias não disponíveis ou vazios');
            }
            
            // Ajustar a visualização para conter todos os elementos
            if (overlayLayers.length > 0) {
                // Criar camada de grupo com todos os elementos
                const group = L.featureGroup(overlayLayers);
                map.fitBounds(group.getBounds(), { padding: [20, 20] });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar dados do mapa:', error);
            mostrarNotificacao('Erro ao carregar dados do mapa. Por favor, recarregue a página.', 'erro');
        });
}

/**
 * Limpa todos os marcadores e camadas do mapa
 */
function limparMapa() {
    console.log('Limpando camadas do mapa...');
    
    // Remover todos os marcadores e camadas overlay
    overlayLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    
    // Limpar arrays
    overlayLayers = [];
    marcadoresPastos = [];
}

/**
 * Processa e adiciona pastos ao mapa
 */
function processarPastos(map, pastos) {
    console.log('Processando pastos:', pastos);
    
    pastos.forEach(pasto => {
        try {
            // Verificar se temos coordenadas
            let lat, lng;
            
            // Tenta extrair as coordenadas de diferentes formatos possíveis
            if (pasto.coordenadas) {
                // Se for um array [lat, lng]
                if (Array.isArray(pasto.coordenadas) && pasto.coordenadas.length >= 2) {
                    lat = pasto.coordenadas[0];
                    lng = pasto.coordenadas[1];
                } 
                // Se for um objeto {lat, lng}
                else if (pasto.coordenadas.lat && pasto.coordenadas.lng) {
                    lat = pasto.coordenadas.lat;
                    lng = pasto.coordenadas.lng;
                }
                // Se for uma string, tenta converter para JSON
                else if (typeof pasto.coordenadas === 'string') {
                    try {
                        const coords = JSON.parse(pasto.coordenadas);
                        if (Array.isArray(coords) && coords.length >= 2) {
                            lat = coords[0];
                            lng = coords[1];
                        } else if (coords.lat && coords.lng) {
                            lat = coords.lat;
                            lng = coords.lng;
                        }
                    } catch (e) {
                        console.error('Erro ao converter coordenadas de pasto:', e);
                    }
                }
            } 
            // Verificar propriedades latitude/longitude individuais
            else if (pasto.latitude && pasto.longitude) {
                lat = pasto.latitude;
                lng = pasto.longitude;
            }
            
            // Se não conseguiu obter coordenadas válidas, ignora esta pasto
            if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
                console.warn(`Pasto ${pasto.nome || pasto.id_pasto} sem coordenadas válidas.`);
                return;
            }
            
            console.log(`Criando marcador para pasto ${pasto.nome || pasto.id_pasto} em [${lat}, ${lng}]`);
            
            // Cria ícone personalizado para pasto
            const iconePasto = L.divIcon({
                className: 'pasto-icon',
                html: `<div class="pasto-icon-container">
                        <div class="icon"><i class="fas fa-tree"></i></div>
                      </div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            // Adiciona marcador ao mapa
            const marker = L.marker([lat, lng], { icon: iconePasto }).addTo(map);
            
            // Adiciona popup com informações
            const nome = pasto.nome || pasto.id_pasto || 'Pasto';
            const popupContent = `
                <div class="popup-content">
                    <h5>${nome}</h5>
                    <p><strong>Área:</strong> ${pasto.area ? pasto.area.toFixed(2) : '0'} ha</p>
                    <p><strong>Animais:</strong> ${pasto.qtd_animais || 0}</p>
                </div>
            `;
            marker.bindPopup(popupContent);
            
            // Adicionar à lista de marcadores de pastos
            marcadoresPastos.push(marker);
            
            // Adicionar à lista de camadas overlay
            overlayLayers.push(marker);
            
        } catch (e) {
            console.error(`Erro ao processar pasto ${pasto.nome || pasto.id_pasto}:`, e);
        }
    });
}

/**
 * Processa e adiciona benfeitorias ao mapa
 */
function processarBenfeitorias(map, benfeitorias) {
    console.log('Processando benfeitorias:', benfeitorias);
    
    benfeitorias.forEach(benfeitoria => {
        try {
            // Verificar se temos coordenadas
            let lat, lng;
            
            // Tenta extrair as coordenadas de diferentes formatos possíveis
            if (benfeitoria.coordenadas) {
                // Se for um array [lat, lng]
                if (Array.isArray(benfeitoria.coordenadas) && benfeitoria.coordenadas.length >= 2) {
                    lat = benfeitoria.coordenadas[0];
                    lng = benfeitoria.coordenadas[1];
                } 
                // Se for um objeto {lat, lng}
                else if (benfeitoria.coordenadas.lat && benfeitoria.coordenadas.lng) {
                    lat = benfeitoria.coordenadas.lat;
                    lng = benfeitoria.coordenadas.lng;
                }
                // Se for uma string, tenta converter para JSON
                else if (typeof benfeitoria.coordenadas === 'string') {
                    try {
                        const coords = JSON.parse(benfeitoria.coordenadas);
                        if (Array.isArray(coords) && coords.length >= 2) {
                            lat = coords[0];
                            lng = coords[1];
                        } else if (coords.lat && coords.lng) {
                            lat = coords.lat;
                            lng = coords.lng;
                        }
                    } catch (e) {
                        console.error('Erro ao converter coordenadas de benfeitoria:', e);
                    }
                }
            } 
            // Verificar propriedades latitude/longitude individuais
            else if (benfeitoria.latitude && benfeitoria.longitude) {
                lat = benfeitoria.latitude;
                lng = benfeitoria.longitude;
            }
            
            // Se não conseguiu obter coordenadas válidas, ignora esta benfeitoria
            if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
                console.warn(`Benfeitoria ${benfeitoria.nome || benfeitoria.id_benfeitoria} sem coordenadas válidas.`);
                return;
            }
            
            console.log(`Criando marcador para benfeitoria ${benfeitoria.nome || benfeitoria.id_benfeitoria} em [${lat}, ${lng}]`);
            
            // Cria ícone personalizado para benfeitoria
            const iconeBenfeitoria = L.divIcon({
                className: 'benfeitoria-icon',
                html: `<div class="benfeitoria-icon-container">
                        <div class="icon"><i class="fas fa-home"></i></div>
                      </div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            // Adiciona marcador ao mapa
            const marker = L.marker([lat, lng], { icon: iconeBenfeitoria }).addTo(map);
            
            // Adiciona popup com informações
            const nome = benfeitoria.nome || benfeitoria.id_benfeitoria || 'Benfeitoria';
            const popupContent = `
                <div class="popup-content">
                    <h5>${nome}</h5>
                    <p><strong>Valor:</strong> R$ ${benfeitoria.valor_compra ? parseFloat(benfeitoria.valor_compra).toLocaleString('pt-BR') : '0,00'}</p>
                    <p><strong>Data aquisição:</strong> ${benfeitoria.data_aquisicao || 'N/A'}</p>
                </div>
            `;
            marker.bindPopup(popupContent);
            
            // Adicionar à lista de camadas overlay
            overlayLayers.push(marker);
            
        } catch (e) {
            console.error(`Erro ao processar benfeitoria ${benfeitoria.nome || benfeitoria.id_benfeitoria}:`, e);
        }
    });
}

/**
 * Exibe uma notificação temporária na interface
 * @param {string} mensagem - Texto da notificação
 * @param {string} tipo - Tipo de notificação: 'sucesso', 'erro', 'aviso', 'info'
 * @param {number} duracao - Duração em milissegundos (padrão: 3000ms)
 */
function mostrarNotificacao(mensagem, tipo = 'info', duracao = 3000) {
    console.log(`Notificação (${tipo}): ${mensagem}`);
    
    // Obter o container de notificações
    const container = document.getElementById('notification-container');
    if (!container) {
        console.error('Container de notificações não encontrado');
        return;
    }
    
    // Definir classe CSS baseada no tipo
    let classeNotificacao = 'notification';
    switch (tipo) {
        case 'sucesso':
            classeNotificacao += ' notification-success';
            break;
        case 'erro':
            classeNotificacao += ' notification-error';
            break;
        case 'aviso':
            classeNotificacao += ' notification-warning';
            break;
        default:
            classeNotificacao += ' notification-info';
    }
    
    // Criar elemento de notificação
    const notificacao = document.createElement('div');
    notificacao.className = classeNotificacao;
    notificacao.textContent = mensagem;
    
    // Adicionar ao container
    container.appendChild(notificacao);
    
    // Aplicar animação de entrada
    setTimeout(() => {
        notificacao.classList.add('show');
    }, 10);
    
    // Remover após o tempo especificado
    setTimeout(() => {
        notificacao.classList.remove('show');
        notificacao.classList.add('hide');
        
        // Remover do DOM após a animação de saída
        setTimeout(() => {
            container.removeChild(notificacao);
        }, 300);
    }, duracao);
}

/**
 * Inicializa os gráficos do dashboard
 */
function initGraficos() {
    // Verificar se há dados já carregados via script
    if (typeof chartData !== 'undefined') {
        processarDadosGraficos(chartData);
    } else {
        // Caso contrário, buscar via AJAX
        fetch('/dashboard/atualizar/')
            .then(response => response.json())
            .then(data => {
                console.log('Dados recebidos para gráficos:', data);
                processarDadosGraficos(data);
            })
            .catch(error => {
                console.error('Erro ao carregar dados para gráficos:', error);
                mostrarNotificacao('Erro ao carregar dados dos gráficos', 'erro');
            });
    }
}

/**
 * Processa os dados recebidos e cria os gráficos
 */
function processarDadosGraficos(data) {
    if (data.evolucao_rebanho && data.evolucao_rebanho.length > 0) {
        criarGraficoRebanho(data.evolucao_rebanho);
    } else {
        console.warn('Dados de evolução do rebanho não disponíveis');
    }
    
    if (data.financeiro && data.financeiro.length > 0) {
        criarGraficoFinanceiro(data.financeiro);
    } else {
        console.warn('Dados financeiros não disponíveis');
    }
}

/**
 * Anima os contadores nos KPIs
 */
function animarContadores() {
    document.querySelectorAll('.counter-value').forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target')) || 0;
        const duration = 1000; // 1 segundo
        const startTime = performance.now();
        const startValue = 0;
        
        function updateCounter(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            
            // Função de easing para uma animação mais suave
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = startValue + (target - startValue) * easeOutQuart;
            
            // Formatar o valor com base no tipo
            if (target % 1 === 0) {
                // Inteiro
                counter.textContent = Math.floor(currentValue).toLocaleString('pt-BR');
            } else {
                // Decimal
                counter.textContent = currentValue.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }
        
        requestAnimationFrame(updateCounter);
    });
}

/**
 * Criar gráfico de evolução do rebanho
 */
function criarGraficoRebanho(dados) {
    const ctx = document.getElementById('grafico-rebanho');
    if (!ctx) {
        console.error('Elemento do gráfico de rebanho não encontrado');
        return;
    }
    
    // Limpar gráfico anterior se existir
    if (window.graficoRebanho) {
        window.graficoRebanho.destroy();
    }
    
    // Preparar dados para o gráfico
    const labels = dados.map(item => item.mes);
    const dataNascimentos = dados.map(item => item.nascimentos || 0);
    const dataVendas = dados.map(item => item.vendas || 0);
    const dataCompras = dados.map(item => item.compras || 0);
    const dataAbates = dados.map(item => item.abates || 0);
    const dataMortes = dados.map(item => item.mortes || 0);
    const dataTotal = dados.map(item => item.total || 0);
    
    // Criar o gráfico
    window.graficoRebanho = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total',
                    data: dataTotal,
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.2)',
                    pointBackgroundColor: '#4e73df',
                    tension: 0.4,
                    yAxisID: 'y',
                    fill: true
                },
                {
                    label: 'Nascimentos',
                    data: dataNascimentos,
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.2)',
                    pointBackgroundColor: '#1cc88a',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                },
                {
                    label: 'Vendas',
                    data: dataVendas,
                    borderColor: '#e74a3b',
                    backgroundColor: 'rgba(231, 74, 59, 0.2)',
                    pointBackgroundColor: '#e74a3b',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                },
                {
                    label: 'Abates',
                    data: dataAbates,
                    borderColor: '#36b9cc',
                    backgroundColor: 'rgba(54, 185, 204, 0.2)',
                    pointBackgroundColor: '#36b9cc',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                },
                {
                    label: 'Compras',
                    data: dataCompras,
                    borderColor: '#f6c23e',
                    backgroundColor: 'rgba(246, 194, 62, 0.2)',
                    pointBackgroundColor: '#f6c23e',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                },
                {
                    label: 'Mortes',
                    data: dataMortes,
                    borderColor: '#858796',
                    backgroundColor: 'rgba(133, 135, 150, 0.2)',
                    pointBackgroundColor: '#858796',
                    tension: 0.4,
                    yAxisID: 'y1',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolução do Rebanho',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Período'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Total de Animais'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Movimentações'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

/**
 * Criar gráfico financeiro
 */
function criarGraficoFinanceiro(dados) {
    const ctx = document.getElementById('grafico-financeiro');
    if (!ctx) {
        console.error('Elemento do gráfico financeiro não encontrado');
        return;
    }
    
    // Limpar gráfico anterior se existir
    if (window.graficoFinanceiro) {
        window.graficoFinanceiro.destroy();
    }
    
    // Extrair os dados
    const labels = dados.map(item => item.mes);
    
    // Dados de receitas
    const dataReceitas = dados.map(item => item.total_receitas || 0);
    const dataVendas = dados.map(item => item.receitas_vendas || 0);
    const dataAbates = dados.map(item => item.receitas_abates || 0);
    const dataOutrasReceitas = dados.map(item => item.outras_receitas || 0);
    
    // Dados de despesas
    const dataDespesas = dados.map(item => item.total_despesas || 0);
    const dataCompras = dados.map(item => item.despesas_compras || 0);
    const dataOpex = dados.map(item => item.despesas_operacionais || 0);
    const dataOutrasDespesas = dados.map(item => item.outras_despesas || 0);
    
    // Lucro
    const dataLucro = dados.map((item, index) => {
        const receitas = item.total_receitas || 0;
        const despesas = item.total_despesas || 0;
        return receitas - despesas;
    });
    
    // Criar o gráfico
    window.graficoFinanceiro = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                // Receitas (barras positivas)
                {
                    label: 'Vendas',
                    data: dataVendas,
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1,
                    stack: 'Receitas'
                },
                {
                    label: 'Abates',
                    data: dataAbates,
                    backgroundColor: 'rgba(23, 162, 184, 0.7)',
                    borderColor: 'rgba(23, 162, 184, 1)',
                    borderWidth: 1,
                    stack: 'Receitas'
                },
                {
                    label: 'Outras Receitas',
                    data: dataOutrasReceitas,
                    backgroundColor: 'rgba(0, 123, 255, 0.7)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 1,
                    stack: 'Receitas'
                },
                
                // Despesas (barras negativas)
                {
                    label: 'Compras',
                    data: dataCompras.map(val => -val),
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1,
                    stack: 'Despesas'
                },
                {
                    label: 'Despesas Operacionais',
                    data: dataOpex.map(val => -val),
                    backgroundColor: 'rgba(255, 193, 7, 0.7)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 1,
                    stack: 'Despesas'
                },
                {
                    label: 'Outras Despesas',
                    data: dataOutrasDespesas.map(val => -val),
                    backgroundColor: 'rgba(108, 117, 125, 0.7)',
                    borderColor: 'rgba(108, 117, 125, 1)',
                    borderWidth: 1,
                    stack: 'Despesas'
                },
                
                // Linha de lucro
                {
                    label: 'Lucro',
                    data: dataLucro,
                    type: 'line',
                    borderColor: 'rgba(90, 30, 220, 1)',
                    backgroundColor: 'rgba(90, 30, 220, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointStyle: 'rectRot',
                    pointRadius: 4,
                    pointBackgroundColor: 'rgba(90, 30, 220, 1)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Receitas vs Despesas',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            let value = context.raw;
                            
                            // Para despesas, revertemos o sinal negativo na exibição
                            if (context.dataset.stack === 'Despesas') {
                                value = Math.abs(value);
                            }
                            
                            return `${label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Período'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Valor (R$)'
                    },
                    ticks: {
                        callback: function(value) {
                            // Formatar valores positivos e negativos como moeda
                            return 'R$ ' + Math.abs(value).toLocaleString('pt-BR', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            });
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Lucro (R$)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

/**
 * Configura listeners de eventos
 */
function setupEventListeners() {
    // Listener para botões de ação rápida
    const acaoRapidaButtons = document.querySelectorAll('.acao-rapida');
    acaoRapidaButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });
    });
}

/**
 * Atualiza todos os dados do dashboard com base na fazenda selecionada
 */
function atualizarDados() {
    // Verificar se há mapa inicializado
    const mapaElement = document.getElementById('mapa-fazenda');
    const map = mapaElement._leaflet_map;
    
    if (map) {
        // Se o mapa já está inicializado, apenas carrega novos dados
        carregarDadosMapa(map);
    } else {
        // Se o mapa não está inicializado, inicializa-o
        initMapa();
    }
    
    // Atualizar gráficos
    fetch('/dashboard/atualizar/?fazenda=' + document.getElementById('fazenda-select').value)
        .then(response => response.json())
        .then(data => {
            console.log('Dados atualizados recebidos:', data);
            processarDadosGraficos(data);
        })
        .catch(error => {
            console.error('Erro ao atualizar dados:', error);
            mostrarNotificacao('Erro ao atualizar dados', 'erro');
        });
}

/**
 * Exibe uma notificação temporária
 */
function showNotification(message, type = 'info') {
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) {
        // Criar área de notificação se não existir
        const container = document.querySelector('.dashboard-container');
        const notificationDiv = document.createElement('div');
        notificationDiv.id = 'notification-area';
        notificationDiv.className = 'position-fixed top-0 end-0 p-3';
        notificationDiv.style.zIndex = '1050';
        container.appendChild(notificationDiv);
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast bg-${type} text-white" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">Notificação</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.getElementById('notification-area').innerHTML = toastHtml;
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
}
