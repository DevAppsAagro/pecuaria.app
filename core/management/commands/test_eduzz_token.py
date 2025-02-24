from django.core.management.base import BaseCommand
from core.eduzz_api import EduzzAPI

class Command(BaseCommand):
    help = 'Testa o token de acesso da Eduzz'

    def handle(self, *args, **options):
        self.stdout.write('Testando token da Eduzz...')
        
        api = EduzzAPI()
        result = api.test_token()
        
        if result:
            self.stdout.write(self.style.SUCCESS('Token válido!'))
            self.stdout.write(f'Detalhes da conta: {result}')
        else:
            self.stdout.write(self.style.ERROR('Token inválido ou erro na API'))
