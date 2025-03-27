"""
Sinais para automatizar tarefas quando eventos específicos ocorrem
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .categoria_replicator import replicar_categorias_globais_para_usuario

@receiver(post_save, sender=User)
def replicar_categorias_para_novo_usuario(sender, instance, created, **kwargs):
    """
    Replica categorias globais para um novo usuário quando ele é criado.
    
    Args:
        sender: Modelo que enviou o sinal (User)
        instance: Instância do usuário que foi salva
        created: True se o usuário foi criado, False se foi atualizado
    """
    if created:
        print(f"Novo usuário criado: {instance.username}. Replicando categorias globais...")
        cat_count, subcat_count = replicar_categorias_globais_para_usuario(instance)
        print(f"Replicação concluída. {cat_count} categorias e {subcat_count} subcategorias criadas.")
