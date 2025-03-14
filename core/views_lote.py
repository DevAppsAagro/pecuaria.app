from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Lote

@login_required
def lote_delete(request, pk):
    lote = get_object_or_404(Lote, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        lote.delete()
        messages.success(request, 'Lote excluído com sucesso!')
        return redirect('lote_list')
    
    return render(request, 'lotes/confirm_delete.html', {
        'object': lote,
        'title': 'Excluir Lote'
    })
