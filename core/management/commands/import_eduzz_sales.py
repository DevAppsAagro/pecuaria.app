from django.core.management.base import BaseCommand
from core.eduzz_api import EduzzAPI
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importa vendas antigas da Eduzz'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando importação de vendas da Eduzz...')
        
        api = EduzzAPI()
        count = api.import_past_sales()
        
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'Importação concluída! {count} vendas importadas.'))
        else:
            self.stdout.write(self.style.WARNING('Nenhuma venda nova encontrada para importar.'))
