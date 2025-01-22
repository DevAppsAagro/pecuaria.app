from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from core.models.configuracoes import *

# Raças
class RacaListView(ListView):
    model = Raca
    template_name = 'configuracoes/raca_list.html'
    context_object_name = 'racas'

# Finalidades de Lote
class FinalidadeLoteListView(ListView):
    model = FinalidadeLote
    template_name = 'configuracoes/finalidade_lote_list.html'
    context_object_name = 'finalidades'

    def get_queryset(self):
        return FinalidadeLote.objects.filter(usuario=self.request.user)

# Categorias de Animais
class CategoriaAnimalListView(ListView):
    model = CategoriaAnimal
    template_name = 'configuracoes/categoria_animal_list.html'
    context_object_name = 'categorias'

# Unidades de Medida
class UnidadeMedidaListView(ListView):
    model = UnidadeMedida
    template_name = 'configuracoes/unidade_medida_list.html'
    context_object_name = 'unidades'

# Motivos de Morte
class MotivoMorteListView(ListView):
    model = MotivoMorte
    template_name = 'configuracoes/motivo_morte_list.html'
    context_object_name = 'motivos'

# Categorias de Custos
class CategoriaCustoListView(ListView):
    model = CategoriaCusto
    template_name = 'configuracoes/categoria_custo_list.html'
    context_object_name = 'categorias'

# Variedades de Capim
class VariedadeCapimListView(ListView):
    model = VariedadeCapim
    template_name = 'configuracoes/variedade_capim_list.html'
    context_object_name = 'variedades'
