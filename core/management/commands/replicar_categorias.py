"""
Comando para replicar categorias globais para usuários
"""
from django.core.management.base import BaseCommand
from core.categoria_replicator import replicar_categorias_globais_para_usuario, replicar_categorias_para_todos_usuarios
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Replica categorias globais para usuários'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            help='Username do usuário para o qual replicar as categorias. Se não for fornecido, replica para todos os usuários.',
            required=False
        )

    def handle(self, *args, **options):
        username = options.get('usuario')
        
        if username:
            try:
                usuario = User.objects.get(username=username)
                self.stdout.write(self.style.SUCCESS(f'Replicando categorias para o usuário {username}...'))
                cat_count, subcat_count = replicar_categorias_globais_para_usuario(usuario)
                self.stdout.write(self.style.SUCCESS(
                    f'Replicação concluída. {cat_count} categorias e {subcat_count} subcategorias criadas.'
                ))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Usuário {username} não encontrado.'))
        else:
            self.stdout.write(self.style.SUCCESS('Replicando categorias para todos os usuários...'))
            stats = replicar_categorias_para_todos_usuarios()
            
            total_cat = sum(stat['categorias'] for stat in stats.values())
            total_subcat = sum(stat['subcategorias'] for stat in stats.values())
            
            self.stdout.write(self.style.SUCCESS(
                f'Replicação concluída. {total_cat} categorias e {total_subcat} subcategorias criadas no total.'
            ))
            
            # Exibe estatísticas por usuário
            for username, stat in stats.items():
                self.stdout.write(
                    f'  {username}: {stat["categorias"]} categorias, {stat["subcategorias"]} subcategorias'
                )
