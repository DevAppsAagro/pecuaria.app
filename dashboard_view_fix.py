@login_required
def dashboard_view(request):
    """
    Redireciona para o dashboard correto
    """
    # Obtém as fazendas do usuário para o filtro
    fazendas = Fazenda.objects.filter(usuario=request.user).order_by('nome')
    # Contexto para o template
    context = {
        'fazendas': fazendas,
    }
    return render(request, 'dashboard.html', context)
