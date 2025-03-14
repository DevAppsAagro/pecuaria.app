from django.urls import path
from . import views_mortes

urlpatterns = [
    # URLs para gerenciamento de mortes
    path('animais/mortes/', views_mortes.morte_list, name='morte_list'),
    path('animais/mortes/nova/', views_mortes.morte_create, name='morte_create'),
    path('animais/mortes/<int:pk>/editar/', views_mortes.morte_update, name='morte_update'),
    path('animais/mortes/<int:pk>/excluir/', views_mortes.morte_delete, name='morte_delete'),
    
    # URLs para AJAX
    path('animais/buscar-animal-ajax/', views_mortes.buscar_animal_ajax, name='buscar_animal_ajax'),
]
