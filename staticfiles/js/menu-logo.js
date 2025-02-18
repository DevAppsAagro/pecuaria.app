$(document).ready(function() {
    // Função para atualizar a visibilidade das logos
    function updateLogoVisibility() {
        if ($('body').hasClass('sidebar-collapse')) {
            $('.logo-sm').show();
            $('.logo-lg').hide();
        } else {
            $('.logo-sm').hide();
            $('.logo-lg').show();
        }
    }

    // Atualiza quando o botão do menu é clicado
    $('[data-widget="pushmenu"]').on('click', function() {
        setTimeout(updateLogoVisibility, 50);
    });

    // Atualiza no carregamento inicial
    updateLogoVisibility();
});
