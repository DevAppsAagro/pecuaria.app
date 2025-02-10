from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Fazenda

@login_required
def selecionar_fazenda(request):
    if request.method == 'POST':
        fazenda_id = request.POST.get('fazenda_id')
        if fazenda_id:
            try:
                fazenda = Fazenda.objects.get(id=fazenda_id, usuario=request.user)
                request.session['fazenda_atual_id'] = fazenda.id
                messages.success(request, f'Fazenda {fazenda.nome} selecionada com sucesso!')
            except Fazenda.DoesNotExist:
                messages.error(request, 'Fazenda não encontrada.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
    
    fazendas = Fazenda.objects.filter(usuario=request.user)
    fazenda_atual_id = request.session.get('fazenda_atual_id')
    return render(request, 'config/selecionar_fazenda.html', {
        'fazendas': fazendas,
        'fazenda_atual_id': fazenda_atual_id
    })
