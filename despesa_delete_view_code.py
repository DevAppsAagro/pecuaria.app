from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from .models import Despesa

class DespesaDeleteView(LoginRequiredMixin, DeleteView):
    model = Despesa
    template_name = 'financeiro/despesa_delete.html'
    success_url = reverse_lazy('despesas_list')

    def get_queryset(self):
        return Despesa.objects.filter(usuario=self.request.user)
