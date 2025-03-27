"""
Patch específico para o método form_valid da classe DespesaCreateView
que corrige o processamento de itens de despesa relacionados a estoque,
especialmente para categorias globais.
"""
import logging
import types
import json
from decimal import Decimal
from django.db import transaction
from .models_estoque import Insumo
from .categoria_utils import is_categoria_estoque

logger = logging.getLogger(__name__)

def processar_item_despesa_estoque(self, despesa, item_despesa, categoria, subcategoria, insumo_data):
    """
    Processa um item de despesa relacionado a estoque, criando ou atualizando o insumo
    e gerando a movimentação de estoque correspondente.
    
    Args:
        despesa: Objeto Despesa
        item_despesa: Objeto ItemDespesa
        categoria: Objeto CategoriaCusto
        subcategoria: Objeto SubcategoriaCusto
        insumo_data: Dicionário com dados do insumo
    
    Returns:
        Objeto Insumo criado ou atualizado
    """
    logger.info(f"Processando item de despesa {item_despesa.id} como estoque")
    logger.info(f"Categoria: {categoria.nome} (ID: {categoria.id}, Alocação: {categoria.alocacao})")
    logger.info(f"Usuário da categoria: {categoria.usuario_id if categoria.usuario_id else 'Global'}")
    logger.info(f"Dados do insumo: {insumo_data}")
    
    # Verifica se é uma categoria de estoque
    if not is_categoria_estoque(categoria):
        logger.warning(f"Categoria {categoria.nome} não é do tipo estoque. Alocação: {categoria.alocacao}")
        return None
    
    # Verifica se há uma fazenda de destino
    if not item_despesa.fazenda_destino:
        logger.warning(f"Item de despesa {item_despesa.id} não tem fazenda de destino definida")
        # Para categorias globais, podemos usar a fazenda principal do usuário se disponível
        if not categoria.usuario_id:  # Se for categoria global
            logger.info("Categoria global detectada, tentando definir fazenda de destino")
            from .models import Fazenda
            try:
                # Tenta encontrar a fazenda principal do usuário
                fazenda_principal = Fazenda.objects.filter(usuario=self.request.user, principal=True).first()
                if fazenda_principal:
                    item_despesa.fazenda_destino = fazenda_principal
                    item_despesa.save()
                    logger.info(f"Fazenda de destino definida automaticamente: {fazenda_principal.nome} (ID: {fazenda_principal.id})")
                else:
                    # Se não encontrar a fazenda principal, tenta pegar qualquer fazenda do usuário
                    qualquer_fazenda = Fazenda.objects.filter(usuario=self.request.user).first()
                    if qualquer_fazenda:
                        item_despesa.fazenda_destino = qualquer_fazenda
                        item_despesa.save()
                        logger.info(f"Fazenda de destino definida automaticamente (não principal): {qualquer_fazenda.nome} (ID: {qualquer_fazenda.id})")
                    else:
                        logger.warning("Não foi possível definir automaticamente a fazenda de destino")
            except Exception as e:
                logger.error(f"Erro ao tentar definir fazenda de destino automaticamente: {str(e)}")
    else:
        logger.info(f"Fazenda de destino já definida: {item_despesa.fazenda_destino.nome} (ID: {item_despesa.fazenda_destino.id})")
    
    # Cria ou obtém o insumo
    if insumo_data.get('id'):
        try:
            insumo = Insumo.objects.get(id=insumo_data['id'])
            logger.info(f"Insumo existente encontrado: {insumo.nome} (ID: {insumo.id})")
        except Insumo.DoesNotExist:
            logger.warning(f"Insumo com ID {insumo_data['id']} não encontrado, criando novo")
            insumo = None
    else:
        insumo = None
        
    if not insumo:
        logger.info(f"Criando novo insumo: {insumo_data['nome']}")
        insumo = Insumo.objects.create(
            nome=insumo_data['nome'],
            categoria=categoria,
            subcategoria=subcategoria,
            unidade_medida_id=insumo_data['unidade_medida_id'],
            usuario=self.request.user
        )
        logger.info(f"Novo insumo criado: {insumo.nome} (ID: {insumo.id})")
    
    # Cria a movimentação de estoque
    from .views_estoque import criar_entrada_estoque_from_despesa
    criar_entrada_estoque_from_despesa(despesa, item_despesa, insumo)
    
    return insumo

def patch_form_valid(views_module):
    """
    Aplica o patch no método form_valid da classe DespesaCreateView.
    
    Args:
        views_module: Módulo views.py que contém a classe DespesaCreateView
    """
    from .views import DespesaCreateView
    
    # Guarda a implementação original do método
    original_form_valid = DespesaCreateView.form_valid
    
    def patched_form_valid(self, form):
        """
        Versão patcheada do método form_valid que corrige o processamento
        de despesas relacionadas a estoque, especialmente para categorias globais.
        """
        logger.info("Executando versão patcheada do método form_valid")
        
        # Adiciona o método processar_item_despesa_estoque à instância
        self.processar_item_despesa_estoque = types.MethodType(processar_item_despesa_estoque, self)
        
        # Guarda os dados originais do formulário antes de processá-lo
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
        
        # Verifica se há itens de despesa que precisam ser reprocessados
        try:
            from .models import ItemDespesa, Fazenda
            from .categoria_utils import is_categoria_estoque
            
            # Obtém todos os itens da despesa
            itens_despesa = self.object.itens.all()
            
            for item in itens_despesa:
                categoria = item.categoria
                
                # Verifica se é uma categoria de estoque
                if is_categoria_estoque(categoria):
                    logger.info(f"Processando item de despesa {item.id} (categoria de estoque)")
                    
                    # Se não tem fazenda de destino, tenta definir com base nos dados do formulário
                    if not item.fazenda_destino:
                        logger.warning(f"Item de despesa {item.id} não tem fazenda de destino definida")
                        
                        # Tenta encontrar o destino_id nos dados do formulário
                        try:
                            itens_data = self.request.POST.get('itens_data')
                            if itens_data:
                                itens_json = json.loads(itens_data)
                                for item_data in itens_json:
                                    # Verifica se este é o item que estamos processando
                                    if (item_data.get('categoria_id') == str(item.categoria_id) and 
                                        item_data.get('subcategoria_id') == str(item.subcategoria_id) and
                                        abs(float(item_data.get('valor_total', 0)) - float(item.valor_total)) < 0.01):
                                        
                                        destino_id = item_data.get('destino_id')
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
                        except Exception as e:
                            logger.error(f"Erro ao processar dados do formulário: {str(e)}")
                        
                        # Se ainda não tem fazenda de destino, tenta definir automaticamente
                        if not item.fazenda_destino:
                            # Para categorias globais, podemos usar qualquer fazenda do usuário
                            if not categoria.usuario_id:  # Se for categoria global
                                logger.info("Categoria global detectada, tentando definir fazenda de destino")
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
            logger.error(f"Erro ao reprocessar itens de despesa: {str(e)}")
        
        return response
    
    # Aplica o patch
    DespesaCreateView.form_valid = patched_form_valid
    
    logger.info("Patch aplicado com sucesso ao método form_valid da classe DespesaCreateView")
    
    return True
