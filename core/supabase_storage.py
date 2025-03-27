import os
import uuid
import logging
from django.conf import settings
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def upload_file_to_supabase(file, bucket_name, old_url=None):
    """
    Faz upload de um arquivo para o Supabase Storage e retorna a URL pública.
    Se old_url for fornecido, o arquivo antigo será removido.
    
    Args:
        file: Arquivo a ser enviado (objeto UploadedFile do Django)
        bucket_name: Nome do bucket no Supabase
        old_url: URL do arquivo antigo a ser removido (opcional)
        
    Returns:
        URL pública do arquivo ou None se falhar
    """
    try:
        # Criar nome único para o arquivo
        file_ext = os.path.splitext(file.name)[1]
        
        # Determinar o prefixo baseado no bucket
        prefix = ""
        if bucket_name == 'profile-photos':
            prefix = "profile_photos"
        elif bucket_name == 'logofazenda':
            prefix = "farm_logos"
        elif bucket_name == 'payment-receipts':
            prefix = "receipts"
        elif bucket_name == 'boletoecomprovante':
            if 'boleto' in file.name.lower():
                prefix = "boletos"
            else:
                prefix = "comprovantes"
        
        # Criar caminho do arquivo com prefixo
        file_name = f"{prefix}/{uuid.uuid4()}{file_ext}"
        
        # Inicializar cliente Supabase
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Upload do arquivo
        result = supabase.storage.from_(bucket_name).upload(
            file_name,
            file.read(),
            {"content-type": file.content_type}
        )
        
        # Gerar URL pública
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        
        # Deletar arquivo antigo se existir
        if old_url:
            try:
                old_file_name = old_url.split('/')[-1]
                
                # Determinar o prefixo baseado no bucket para o arquivo antigo
                old_prefix = ""
                if bucket_name == 'profile-photos':
                    old_prefix = "profile_photos"
                elif bucket_name == 'logofazenda':
                    old_prefix = "farm_logos"
                elif bucket_name == 'payment-receipts':
                    old_prefix = "receipts"
                elif bucket_name == 'boletoecomprovante':
                    if 'boleto' in old_url.lower():
                        old_prefix = "boletos"
                    else:
                        old_prefix = "comprovantes"
                
                old_path = f"{old_prefix}/{old_file_name}"
                supabase.storage.from_(bucket_name).remove([old_path])
                logger.info(f"Arquivo antigo removido: {old_path}")
            except Exception as e:
                logger.error(f"Erro ao remover arquivo antigo: {str(e)}")
        
        return public_url
    except Exception as e:
        logger.error(f"Erro ao fazer upload para o Supabase: {str(e)}")
        return None

def remove_file_from_supabase(url, bucket_name):
    """
    Remove um arquivo do Supabase Storage.
    
    Args:
        url: URL pública do arquivo a ser removido
        bucket_name: Nome do bucket no Supabase
        
    Returns:
        True se o arquivo foi removido com sucesso, False caso contrário
    """
    try:
        if not url:
            return True
            
        # Extrair nome do arquivo da URL
        file_name = url.split('/')[-1]
        
        # Determinar o prefixo baseado no bucket
        prefix = ""
        if bucket_name == 'profile-photos':
            prefix = "profile_photos"
        elif bucket_name == 'logofazenda':
            prefix = "farm_logos"
        elif bucket_name == 'payment-receipts':
            prefix = "receipts"
        elif bucket_name == 'boletoecomprovante':
            if 'boleto' in url.lower():
                prefix = "boletos"
            else:
                prefix = "comprovantes"
        
        path = f"{prefix}/{file_name}"
        
        # Inicializar cliente Supabase
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Remover arquivo
        supabase.storage.from_(bucket_name).remove([path])
        logger.info(f"Arquivo removido com sucesso: {path}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao remover arquivo do Supabase: {str(e)}")
        return False
