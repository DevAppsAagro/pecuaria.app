// Função para aplicar os filtros
function aplicarFiltros() {
    const fazendaId = document.getElementById('filtro-fazenda').value;
    const loteId = document.getElementById('filtro-lote').value;
    
    let url = window.location.pathname + '?';
    const params = [];
    
    if (fazendaId) {
        params.push('fazenda=' + fazendaId);
    }
    if (loteId) {
        params.push('lote=' + loteId);
    }
    
    window.location.href = url + params.join('&');
}

// Adiciona eventos aos filtros quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    const filtroFazenda = document.getElementById('filtro-fazenda');
    const filtroLote = document.getElementById('filtro-lote');
    
    if (filtroFazenda) {
        filtroFazenda.addEventListener('change', aplicarFiltros);
    }
    
    if (filtroLote) {
        filtroLote.addEventListener('change', aplicarFiltros);
    }
});
