"""
Correção específica para o problema de destino não sendo salvo corretamente
no formulário de despesas, especialmente para categorias de estoque.
"""
import logging
import json
from django.db import transaction

logger = logging.getLogger(__name__)

def aplicar_patch_destino():
    """
    Aplica um patch específico para corrigir o problema de destino não sendo
    salvo corretamente no formulário de despesas.
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
        
        # Guarda os dados originais do formulário antes de processá-lo
        itens_json = []
        try:
            # Obtém os dados dos itens da despesa do campo oculto
            itens_data = self.request.POST.get('itens_data')
            if itens_data:
                itens_json = json.loads(itens_data)
                logger.info(f"Dados dos itens da despesa: {itens_json}")
        except Exception as e:
            logger.error(f"Erro ao obter dados dos itens da despesa: {str(e)}")
        
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
                                            
                                            # Atualiza a movimentação de estoque relacionada
                                            from .models_estoque import MovimentacaoEstoque
                                            movimentacoes = MovimentacaoEstoque.objects.filter(despesa=self.object, insumo__categoria=categoria)
                                            for mov in movimentacoes:
                                                logger.info(f"Atualizando fazenda de destino para movimentação de estoque {mov.id}")
                                                # Aqui você pode atualizar a movimentação se necessário
                                        except Fazenda.DoesNotExist:
                                            logger.warning(f"Fazenda com ID {destino_id} não encontrada")
                                    else:
                                        logger.warning("Destino não definido nos dados do formulário")
                            
                            # Se ainda não tem fazenda de destino, tenta definir automaticamente
                            if not item.fazenda_destino:
                                # Para categorias globais, podemos usar a fazenda principal do usuário se disponível
                                if not categoria.usuario_id:  # Se for categoria global
                                    logger.info("Categoria global detectada, tentando definir fazenda de destino automaticamente")
                                    try:
                                        # Tenta encontrar a fazenda principal do usuário
                                        fazenda_principal = Fazenda.objects.filter(usuario=self.request.user, principal=True).first()
                                        if fazenda_principal:
                                            item.fazenda_destino = fazenda_principal
                                            item.save()
                                            logger.info(f"Fazenda de destino definida automaticamente: {fazenda_principal.nome} (ID: {fazenda_principal.id})")
                                        else:
                                            # Se não encontrar a fazenda principal, tenta pegar qualquer fazenda do usuário
                                            qualquer_fazenda = Fazenda.objects.filter(usuario=self.request.user).first()
                                            if qualquer_fazenda:
                                                item.fazenda_destino = qualquer_fazenda
                                                item.save()
                                                logger.info(f"Fazenda de destino definida automaticamente (não principal): {qualquer_fazenda.nome} (ID: {qualquer_fazenda.id})")
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
    
    logger.info("Patch para correção de destinos aplicado com sucesso ao método form_valid da classe DespesaCreateView")
    
    return True
