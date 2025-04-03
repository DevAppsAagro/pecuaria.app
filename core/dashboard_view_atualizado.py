@login_required
def dashboard_view(request):
    """
    Redireciona para o dashboard simples
    """
    # Redirecionamento para o novo dashboard simples
    return redirect('dashboard_simples')
