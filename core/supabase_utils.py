import logging
from django.conf import settings
from .supabase_storage import upload_file_to_supabase, remove_file_from_supabase

logger = logging.getLogger(__name__)

def process_despesa_files(form, instance, request):
    """
    Processa os arquivos de comprovante e boleto para uma despesa,
    fazendo upload para o Supabase no bucket 'boletoecomprovante'.
    
    Args:
        form: O formulário com os dados da despesa
        instance: A instância do modelo Despesa
        request: A requisição HTTP
        
    Returns:
        A instância do modelo Despesa atualizada
    """
    try:
        # Processa o arquivo de comprovante
        arquivo = form.cleaned_data.get('arquivo')
        if arquivo and hasattr(arquivo, 'read'):
            # Faz upload do novo arquivo para o bucket 'boletoecomprovante'
            arquivo_url = upload_file_to_supabase(arquivo, settings.SUPABASE_BOLETOS_BUCKET)
            if arquivo_url:
                # O Django já vai salvar o arquivo no campo 'arquivo'
                # Não precisamos fazer nada aqui
                pass
        
        # Processa o boleto
        boleto = form.cleaned_data.get('boleto')
        if boleto and hasattr(boleto, 'read'):
            # Faz upload do novo boleto para o bucket 'boletoecomprovante'
            boleto_url = upload_file_to_supabase(boleto, settings.SUPABASE_BOLETOS_BUCKET)
            if boleto_url:
                # O Django já vai salvar o arquivo no campo 'boleto'
                # Não precisamos fazer nada aqui
                pass
        
        return instance
    except Exception as e:
        logger.error(f"Erro ao processar arquivos da despesa: {str(e)}")
        return instance
