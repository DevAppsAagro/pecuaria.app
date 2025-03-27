"""
Correção específica para o problema de destino não sendo salvo corretamente
no formulário de despesas, especialmente para categorias de estoque.
"""
import logging
import json
from django.db import transaction

logger = logging.getLogger(__name__)

def aplicar_patch_destino_direto():
    """
    Aplica um patch direto para corrigir o problema de destino não sendo
    salvo corretamente no formulário de despesas.
    """
    from .views import DespesaCreateView
    
    # Guarda a implementação original do método
    original_post = DespesaCreateView.post
    
    def patched_post(self, request, *args, **kwargs):
        """
        Versão patcheada do método post que corrige o processamento
        de destinos para itens de despesa relacionados a estoque.
        """
        logger.info("Executando versão patcheada do método post para correção de destinos")
        
        # Guarda os dados originais do formulário
        try:
            # Obtém os dados dos itens da despesa do campo oculto
            itens_data = request.POST.get('itens_data')
            if itens_data:
                itens_json = json.loads(itens_data)
                logger.info(f"Dados dos itens da despesa: {itens_json}")
                
                # Verifica se há destinos definidos
                for item in itens_json:
                    destino_id = item.get('destino_id')
                    if destino_id and destino_id != 'null' and destino_id != '':
                        logger.info(f"Destino encontrado para item com categoria {item.get('categoria_id')}: {destino_id}")
                    else:
                        logger.warning(f"Destino não definido para item com categoria {item.get('categoria_id')}")
        except Exception as e:
            logger.error(f"Erro ao processar dados do formulário: {str(e)}")
        
        # Chama a implementação original
        return original_post(self, request, *args, **kwargs)
    
    # Aplica o patch
    DespesaCreateView.post = patched_post
    
    # Patch para o método que processa os itens da despesa
    from .views import criar_item_despesa
    original_criar_item_despesa = criar_item_despesa
    
    def patched_criar_item_despesa(despesa, item_data):
        """
        Versão patcheada da função criar_item_despesa que corrige o processamento
        de destinos para itens de despesa relacionados a estoque.
        """
        logger.info(f"Executando versão patcheada da função criar_item_despesa para item: {item_data}")
        
        # Verifica se há um destino definido
        destino_id = item_data.get('destino_id')
        if destino_id and destino_id != 'null' and destino_id != '':
            logger.info(f"Destino encontrado: {destino_id}")
        else:
            logger.warning(f"Destino não definido para item com categoria {item_data.get('categoria_id')}")
        
        # Chama a implementação original
        item_despesa = original_criar_item_despesa(despesa, item_data)
        
        # Verifica se o item foi criado e se é uma categoria de estoque
        if item_despesa:
            from .categoria_utils import is_categoria_estoque
            if is_categoria_estoque(item_despesa.categoria):
                logger.info(f"Item de despesa {item_despesa.id} é uma categoria de estoque")
                
                # Verifica se o destino foi definido corretamente
                if not item_despesa.fazenda_destino_id and destino_id and destino_id != 'null' and destino_id != '':
                    logger.info(f"Definindo fazenda de destino para item {item_despesa.id}: {destino_id}")
                    item_despesa.fazenda_destino_id = destino_id
                    item_despesa.save()
        
        return item_despesa
    
    # Substitui a função original pela versão patcheada
    import sys
    sys.modules[__name__].criar_item_despesa = patched_criar_item_despesa
    
    logger.info("Patch para correção de destinos aplicado com sucesso")
    
    return True

# Função para corrigir diretamente o método form_valid
def corrigir_form_valid():
    """
    Corrige diretamente o método form_valid da classe DespesaCreateView
    para garantir que o destino seja corretamente atribuído.
    """
    from .views import DespesaCreateView
    
    # Guarda a implementação original do método
    original_form_valid = DespesaCreateView.form_valid
    
    def patched_form_valid(self, form):
        """
        Versão patcheada do método form_valid que corrige o processamento
        de destinos para itens de despesa relacionados a estoque.
        """
        logger.info("Executando versão patcheada do método form_valid para correção de destinos")
        
        # Guarda os dados originais do formulário
        itens_json = []
        try:
            # Obtém os dados dos itens da despesa do campo oculto
            itens_data = self.request.POST.get('itens_data')
            if itens_data:
                itens_json = json.loads(itens_data)
                logger.info(f"Dados dos itens da despesa: {itens_json}")
        except Exception as e:
            logger.error(f"Erro ao processar dados do formulário: {str(e)}")
        
        # Chama a implementação original
        response = original_form_valid(self, form)
        
        # Corrige os destinos dos itens de despesa
        try:
            from .models import ItemDespesa, Fazenda
            from .categoria_utils import is_categoria_estoque
            
            # Obtém todos os itens da despesa
            itens_despesa = self.object.itens.all()
            
            with transaction.atomic():
                for item in itens_despesa:
                    categoria = item.categoria
                    
                    # Verifica se é uma categoria de estoque
                    if is_categoria_estoque(categoria):
                        logger.info(f"Processando destino para item de despesa {item.id} (categoria de estoque)")
                        
                        # Se não tem fazenda de destino, tenta definir com base nos dados do formulário
                        if not item.fazenda_destino:
                            logger.warning(f"Item de despesa {item.id} não tem fazenda de destino definida")
                            
                            # Tenta encontrar o destino_id nos dados do formulário
                            for item_data in itens_json:
                                # Verifica se este é o item que estamos processando
                                if (item_data.get('categoria_id') == str(item.categoria_id) and 
                                    item_data.get('subcategoria_id') == str(item.subcategoria_id) and
                                    abs(float(item_data.get('valor_total', 0)) - float(item.valor_total)) < 0.01):
                                    
                                    destino_id = item_data.get('destino_id')
                                    logger.info(f"Encontrado item no formulário: {item_data}")
                                    
                                    if destino_id and destino_id != 'null' and destino_id != '':
                                        logger.info(f"Encontrado destino_id nos dados do formulário: {destino_id}")
                                        try:
                                            fazenda = Fazenda.objects.get(id=destino_id)
                                            item.fazenda_destino = fazenda
                                            item.save()
                                            logger.info(f"Fazenda de destino definida: {fazenda.nome} (ID: {fazenda.id})")
                                        except Fazenda.DoesNotExist:
                                            logger.warning(f"Fazenda com ID {destino_id} não encontrada")
                                    else:
                                        logger.warning("Destino não definido nos dados do formulário")
                            
                            # Se ainda não tem fazenda de destino, tenta definir automaticamente
                            if not item.fazenda_destino:
                                # Para categorias globais, podemos usar qualquer fazenda do usuário
                                if not categoria.usuario_id:  # Se for categoria global
                                    logger.info("Categoria global detectada, tentando definir fazenda de destino automaticamente")
                                    try:
                                        # Tenta encontrar qualquer fazenda do usuário
                                        qualquer_fazenda = Fazenda.objects.filter(usuario=self.request.user).first()
                                        if qualquer_fazenda:
                                            item.fazenda_destino = qualquer_fazenda
                                            item.save()
                                            logger.info(f"Fazenda de destino definida automaticamente: {qualquer_fazenda.nome} (ID: {qualquer_fazenda.id})")
                                        else:
                                            logger.warning("Não foi possível definir automaticamente a fazenda de destino")
                                    except Exception as e:
                                        logger.error(f"Erro ao tentar definir fazenda de destino automaticamente: {str(e)}")
                        else:
                            logger.info(f"Fazenda de destino já definida: {item.fazenda_destino.nome} (ID: {item.fazenda_destino.id})")
        except Exception as e:
            logger.error(f"Erro ao corrigir destinos dos itens de despesa: {str(e)}")
        
        return response
    
    # Aplica o patch
    DespesaCreateView.form_valid = patched_form_valid
    
    logger.info("Patch para correção de destinos no método form_valid aplicado com sucesso")
    
    return True
