from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db.models import Q
import pandas as pd
from decimal import Decimal
from datetime import datetime
import numpy as np
import uuid
import decimal
from .models import Animal, Lote, CategoriaAnimal, Raca, Pasto, Fazenda, FinalidadeLote
import traceback
import json
from io import BytesIO

@login_required
def gerar_template_animais(request):
    """Gera um modelo de planilha Excel limpa para importação de animais."""
    # Criar o DataFrame com apenas os cabeçalhos necessários
    colunas = [
        'brinco visual*', 
        'brinco eletrônico', 
        'nome do lote*',
        'raça*',
        'categoria*',
        'pasto atual*',
        'data de nascimento* (dd/mm/aaaa)',
        'data de entrada* (dd/mm/aaaa)',
        'peso de entrada (kg)*',
        'valor de compra (r$)*',
        'brinco pai',
        'brinco mãe',
        'observações'
    ]
    
    # Criar um DataFrame vazio com as colunas
    df = pd.DataFrame(columns=colunas)
    
    # Adicionar uma linha de exemplo (opcional)
    df.loc[0] = ['BR0001', '', 'ENGORDA', 'NELORE', 'NOVILHO', 'PASTO 1', '01/01/2023', '01/01/2025', '450', '0', '', '', '']
    
    # Criar um buffer de bytes para salvar o arquivo Excel
    buffer = BytesIO()
    
    # Salvar o DataFrame no buffer como um arquivo Excel
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Animais')
        
        # Ajustar a largura das colunas para melhor visualização
        worksheet = writer.sheets['Animais']
        for i, col in enumerate(df.columns):
            worksheet.column_dimensions[chr(65 + i)].width = 20
        
        # Aplicar formatação para tornar a planilha mais profissional
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        # Estilo para cabeçalhos
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Aplicar estilo aos cabeçalhos
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
    
    # Definir a resposta HTTP com o arquivo Excel
    buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d')
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=template_importacao_animais_{timestamp}.xlsx'
    
    return response

@login_required
def import_animais(request):
    """Versão simplificada da função para importar animais a partir de uma planilha Excel."""
    context = {
        'active_page': 'importacao_animais',
        'fazendas': Fazenda.objects.filter(usuario=request.user),
        'racas': Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)),
        'categorias': CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)),
        'template_url': '/importacao/animais/template/',
    }
    
    if request.method != 'POST' or 'arquivo' not in request.FILES:
        return render(request, 'animais/animal_import.html', context)
    
    try:
        # Obter o arquivo
        arquivo = request.FILES['arquivo']
        
        # Primeiro, tentar ler o arquivo com configurações otimizadas
        print("\n=== LENDO ARQUIVO EXCEL ===")
        print(f"Nome do arquivo: {arquivo.name}")
        try:
            # Configurar opções de leitura mais robustas
            df = pd.read_excel(
                arquivo,
                keep_default_na=False,  # Evitar que strings vazias se tornem NaN
                na_values=['NA', 'N/A', '#N/A', '#NA', 'NULL'],  # Valores explícitos para NaN
            )
            print(f"Arquivo Excel lido com sucesso. Formato: {df.shape[0]} linhas x {df.shape[1]} colunas")
            
            # Verificar se temos dados suficientes
            if len(df) == 0 or len(df.columns) < 5:
                raise ValueError("Planilha com dados insuficientes")
                
            # Normalizar nomes das colunas
            df.columns = [str(col).strip().lower() for col in df.columns]
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao ler a planilha: {str(e)}. Verifique se o arquivo está no formato correto.'
            })
        
        # Log para depuração
        print(f"\n=== INICIANDO IMPORTAÇÃO DE ANIMAIS ===\nColunas encontradas: {list(df.columns)}")
        
        # Mapeamento de colunas necessárias
        colunas_necessarias = {
            'brinco_visual': ['brinco', 'visual', 'id', 'identificação', 'identificacao', 'numero', 'código', 'codigo', 'tag', 
                            'brinco visual', 'identificador', 'código animal', 'codigo animal', 'numero animal'],
            'lote': ['lote', 'grupo', 'nome lote', 'nomelote', 'nome_lote', 'lote nome', 'nome do lote', 'lotes'],
            'raca': ['raça', 'raca', 'breed', 'tipo de animal', 'genetica', 'genética', 'origem', 'tipo', 'raças', 'racas'],
            'categoria': ['categoria', 'tipo', 'classe', 'classificação', 'classificacao', 'group', 'grupo', 'categorias'],
            'pasto': ['pasto', 'paddock', 'area', 'área', 'local', 'localização', 'localizacao', 'pasto atual', 'pastos', 'pasto atual']
        }
        
        # Mapeamento de colunas encontradas
        mapeamento = {}
        for campo_sistema, alternativas in colunas_necessarias.items():
            print(f"\nBuscando coluna para {campo_sistema}:")
            # Verificar cada coluna da planilha
            for coluna in df.columns:
                coluna_lower = coluna.lower()
                # Verificar match exato
                if coluna_lower == campo_sistema:
                    mapeamento[campo_sistema] = coluna
                    print(f"  - Encontrado match exato: '{coluna}'")
                    break
                
                # Verificar alternativas
                for alt in alternativas:
                    if alt in coluna_lower or coluna_lower in alt:
                        mapeamento[campo_sistema] = coluna
                        print(f"  - Encontrado por alternativa '{alt}': '{coluna}'")
                        break
                        
                if campo_sistema in mapeamento:
                    break
                    
            # Se ainda não encontrou, tentar buscar por posição
            if campo_sistema not in mapeamento and len(df.columns) >= 5:
                posicoes_padrao = {
                    'brinco_visual': 0,  # Geralmente primeira coluna
                    'lote': 1,          # Geralmente segunda coluna
                    'raca': 2,           # Geralmente terceira coluna
                    'categoria': 3,      # Geralmente quarta coluna
                    'pasto': 4           # Geralmente quinta coluna
                }
                
                pos = posicoes_padrao.get(campo_sistema)
                if pos is not None and pos < len(df.columns):
                    mapeamento[campo_sistema] = df.columns[pos]
                    print(f"  - Encontrado por posição padrão {pos}: '{df.columns[pos]}'")
            
            if campo_sistema not in mapeamento:
                print(f"  - NÃO ENCONTRADO")
        
        # Verificar se encontramos todas as colunas necessárias
        colunas_faltantes = []
        for campo in colunas_necessarias:
            if campo not in mapeamento:
                colunas_faltantes.append(campo)
        
        if colunas_faltantes:
            return JsonResponse({
                'status': 'error',
                'message': f'Não foi possível encontrar as seguintes colunas necessárias: {", ".join(colunas_faltantes)}.'
            })
        
        # Pular as primeiras linhas, que podem conter informações de título
        # Só processamos a partir da linha 2 (index 1), pois a linha 0 é o cabeçalho e a linha 1 pode ser instruções ou títulos
        print(f"\n=== PROCESSANDO LINHAS ===\nTotal de linhas: {len(df)}")
        
        # Processar as linhas
        animais_importados = 0
        erros = []
        
        # Mostrar as primeiras 5 linhas para debug
        print("\nPrimeiras 5 linhas da planilha:")
        for i in range(min(5, len(df))):
            print(f"Linha {i}: {dict(df.iloc[i])}")
        
        # Pular o processamento se tivermos menos de 2 linhas (apenas cabeçalho e possivelmente título)
        if len(df) <= 1:
            erros.append("A planilha não contém dados de animais. Preencha a planilha com os dados e tente novamente.")
            return JsonResponse({
                'status': 'error',
                'message': "A planilha não contém dados para importação.",
                'errors': erros
            })
        
        # Iterar por todas as linhas de dados (o cabeçalho já foi excluído pelo pandas)
        for idx in range(0, len(df)):
            try:
                row = df.iloc[idx]
                print(f"\nProcessando linha {idx+1}:")
                
                # Extrair dados obrigatórios
                try:
                    brinco_visual_raw = row[mapeamento['brinco_visual']]
                    print(f"  brinco_visual_raw = {brinco_visual_raw} (tipo: {type(brinco_visual_raw).__name__})")
                    
                    lote_nome_raw = row[mapeamento['lote']]
                    print(f"  lote_nome_raw = {lote_nome_raw}")
                    
                    raca_nome_raw = row[mapeamento['raca']]
                    print(f"  raca_nome_raw = {raca_nome_raw}")
                    
                    categoria_nome_raw = row[mapeamento['categoria']]
                    print(f"  categoria_nome_raw = {categoria_nome_raw}")
                    
                    pasto_nome_raw = row[mapeamento['pasto']]
                    print(f"  pasto_nome_raw = {pasto_nome_raw}")
                except Exception as e:
                    print(f"  ERRO ao acessar colunas: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao ler colunas - {str(e)}")
                    continue
                
                # Verificar se os campos obrigatórios estão preenchidos
                if pd.isna(brinco_visual_raw) or pd.isna(lote_nome_raw) or pd.isna(raca_nome_raw) or pd.isna(categoria_nome_raw) or pd.isna(pasto_nome_raw):
                    erros.append(f"Linha {idx+1}: Um ou mais campos obrigatórios estão vazios.")
                    print("  ERRO: Campos obrigatórios vazios")
                    continue
                
                # Converter para string
                brinco_visual = str(brinco_visual_raw).strip()
                lote_nome = str(lote_nome_raw).strip()
                raca_nome = str(raca_nome_raw).strip()
                categoria_nome = str(categoria_nome_raw).strip()
                pasto_nome = str(pasto_nome_raw).strip()
                
                # Verificar se o animal já existe
                if Animal.objects.filter(brinco_visual=brinco_visual).exists():
                    erros.append(f"Linha {idx+1}: Animal com brinco visual '{brinco_visual}' já existe.")
                    continue
                
                # Obter a fazenda selecionada na planilha (ou a primeira fazenda do usuário)
                try:
                    # Verificar se temos uma coluna de fazenda
                    if 'fazenda' in mapeamento and not pd.isna(row[mapeamento['fazenda']]):
                        fazenda_nome = str(row[mapeamento['fazenda']]).strip()
                        try:
                            fazenda = Fazenda.objects.get(nome=fazenda_nome, usuario=request.user)
                        except Fazenda.DoesNotExist:
                            # Tentar busca fuzzy
                            fazendas = Fazenda.objects.filter(nome__icontains=fazenda_nome, usuario=request.user)
                            if fazendas.exists():
                                fazenda = fazendas.first()
                            else:
                                # Usar a primeira fazenda do usuário
                                fazenda = Fazenda.objects.filter(usuario=request.user).first()
                    else:
                        # Usar a primeira fazenda do usuário
                        fazenda = Fazenda.objects.filter(usuario=request.user).first()
                        
                    if not fazenda:
                        print("  ✗ Nenhuma fazenda encontrada para o usuário")
                        erros.append(f"Linha {idx+1}: Não foi possível identificar uma fazenda. Certifique-se de que você tem pelo menos uma fazenda cadastrada.")
                        continue
                        
                    print(f"  Usando fazenda: {fazenda.nome} (ID: {fazenda.id})")
                    
                except Exception as e:
                    print(f"  ✗ Erro ao obter fazenda: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao obter fazenda - {str(e)}")
                    continue
                    
                # Buscar lote existente
                print(f"  Buscando lote: '{lote_nome}'")
                try:
                    # Tentar localizar o lote diretamente pelo id_lote
                    try:
                        lote = Lote.objects.get(id_lote=lote_nome, usuario=request.user)
                        print(f"  ✓ Lote encontrado: {lote.id_lote} (ID: {lote.id})")
                    except Lote.DoesNotExist:
                        # Se não encontrar, tentar busca case insensitive
                        lotes = Lote.objects.filter(id_lote__iexact=lote_nome, usuario=request.user)
                        if lotes.exists():
                            lote = lotes.first()
                            print(f"  ✓ Lote encontrado (case insensitive): {lote.id_lote} (ID: {lote.id})")
                        else:
                            # Ainda não encontrado, tentar busca por contenção
                            lotes = Lote.objects.filter(id_lote__icontains=lote_nome, usuario=request.user)
                            if lotes.exists():
                                lote = lotes.first()
                                print(f"  ✓ Lote encontrado (contendo): {lote.id_lote} (ID: {lote.id})")
                            else:
                                # Lote não encontrado
                                print(f"  ✗ Lote '{lote_nome}' não encontrado na base de dados")
                                erros.append(f"Linha {idx+1}: Lote '{lote_nome}' não encontrado. Este lote precisa ser criado antes da importação.")
                                continue
                except Exception as e:
                    print(f"  ✗ Erro ao buscar/criar lote: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao processar lote '{lote_nome}' - {str(e)}")
                    continue
                
                # Buscar raça existente
                print(f"  Buscando raça: '{raca_nome}'")
                try:
                    # Tentar localizar a raça diretamente pelo nome
                    try:
                        raca = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(nome=raca_nome)
                        print(f"  ✓ Raça encontrada: {raca.nome} (ID: {raca.id})")
                    except Raca.DoesNotExist:
                        # Se não encontrar, tentar busca case insensitive
                        racas = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).filter(nome__iexact=raca_nome)
                        if racas.exists():
                            raca = racas.first()
                            print(f"  ✓ Raça encontrada (case insensitive): {raca.nome} (ID: {raca.id})")
                        else:
                            # Ainda não encontrado, tentar busca por contenção
                            racas = Raca.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).filter(nome__icontains=raca_nome)
                            if racas.exists():
                                raca = racas.first()
                                print(f"  ✓ Raça encontrada (contendo): {raca.nome} (ID: {raca.id})")
                            else:
                                # Raça não encontrada
                                print(f"  ✗ Raça '{raca_nome}' não encontrada na base de dados")
                                erros.append(f"Linha {idx+1}: Raça '{raca_nome}' não encontrada. Esta raça precisa ser criada antes da importação.")
                                continue
                except Exception as e:
                    print(f"  ✗ Erro ao buscar/criar raça: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao processar raça '{raca_nome}' - {str(e)}")
                    continue
                
                # Buscar categoria existente
                print(f"  Buscando categoria: '{categoria_nome}'")
                try:
                    # Tentar localizar a categoria diretamente pelo nome
                    try:
                        categoria = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).get(nome=categoria_nome)
                        print(f"  ✓ Categoria encontrada: {categoria.nome} (ID: {categoria.id})")
                    except CategoriaAnimal.DoesNotExist:
                        # Se não encontrar, tentar busca case insensitive
                        categorias = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).filter(nome__iexact=categoria_nome)
                        if categorias.exists():
                            categoria = categorias.first()
                            print(f"  ✓ Categoria encontrada (case insensitive): {categoria.nome} (ID: {categoria.id})")
                        else:
                            # Ainda não encontrado, tentar busca por contenção
                            categorias = CategoriaAnimal.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)).filter(nome__icontains=categoria_nome)
                            if categorias.exists():
                                categoria = categorias.first()
                                print(f"  ✓ Categoria encontrada (contendo): {categoria.nome} (ID: {categoria.id})")
                            else:
                                # Categoria não encontrada
                                print(f"  ✗ Categoria '{categoria_nome}' não encontrada na base de dados")
                                erros.append(f"Linha {idx+1}: Categoria '{categoria_nome}' não encontrada. Esta categoria precisa ser criada antes da importação.")
                                continue
                except Exception as e:
                    print(f"  ✗ Erro ao buscar/criar categoria: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao processar categoria '{categoria_nome}' - {str(e)}")
                    continue
                
                # Buscar pasto existente
                print(f"  Buscando pasto: '{pasto_nome}' na fazenda {lote.fazenda.nome}")
                try:
                    # Busca mais abrangente para pastos
                    encontrado = False
                    
                    # 1. Tentar pelo nome exato
                    try:
                        pasto = Pasto.objects.get(nome=pasto_nome, fazenda=lote.fazenda)
                        print(f"  ✓ Pasto encontrado pelo nome: {pasto.nome} (ID: {pasto.id})")
                        encontrado = True
                    except Pasto.DoesNotExist:
                        pass
                    
                    # 2. Tentar pelo id_pasto exato
                    if not encontrado:
                        try:
                            pasto = Pasto.objects.get(id_pasto=pasto_nome, fazenda=lote.fazenda)
                            print(f"  ✓ Pasto encontrado pelo id_pasto: {pasto.id_pasto} (ID: {pasto.id})")
                            encontrado = True
                        except Pasto.DoesNotExist:
                            pass
                    
                    # 3. Busca case insensitive pelo nome
                    if not encontrado:
                        pastos = Pasto.objects.filter(nome__iexact=pasto_nome, fazenda=lote.fazenda)
                        if pastos.exists():
                            pasto = pastos.first()
                            print(f"  ✓ Pasto encontrado (nome case insensitive): {pasto.nome} (ID: {pasto.id})")
                            encontrado = True
                    
                    # 4. Busca case insensitive pelo id_pasto
                    if not encontrado:
                        pastos = Pasto.objects.filter(id_pasto__iexact=pasto_nome, fazenda=lote.fazenda)
                        if pastos.exists():
                            pasto = pastos.first()
                            print(f"  ✓ Pasto encontrado (id_pasto case insensitive): {pasto.id_pasto} (ID: {pasto.id})")
                            encontrado = True
                    
                    # 5. Busca por contenção no nome
                    if not encontrado:
                        pastos = Pasto.objects.filter(nome__icontains=pasto_nome, fazenda=lote.fazenda)
                        if pastos.exists():
                            pasto = pastos.first()
                            print(f"  ✓ Pasto encontrado (nome contém): {pasto.nome} (ID: {pasto.id})")
                            encontrado = True
                    
                    # 6. Busca por contenção no id_pasto
                    if not encontrado:
                        pastos = Pasto.objects.filter(id_pasto__icontains=pasto_nome, fazenda=lote.fazenda)
                        if pastos.exists():
                            pasto = pastos.first()
                            print(f"  ✓ Pasto encontrado (id_pasto contém): {pasto.id_pasto} (ID: {pasto.id})")
                            encontrado = True
                    
                    # 7. Última tentativa - listar todos os pastos da fazenda
                    if not encontrado:
                        pastos = Pasto.objects.filter(fazenda=lote.fazenda)
                        print(f"\n  Pastos disponíveis na fazenda {lote.fazenda.nome}:")
                        for p in pastos:
                            print(f"  - Nome: '{p.nome}', ID_Pasto: '{p.id_pasto}', ID: {p.id}")
                        
                        # Pasto não encontrado
                        print(f"  ✗ Pasto '{pasto_nome}' não encontrado na fazenda {lote.fazenda.nome}")
                        erros.append(f"Linha {idx+1}: Pasto '{pasto_nome}' não encontrado na fazenda {lote.fazenda.nome}. Este pasto precisa ser criado antes da importação.")
                        continue
                except Exception as e:
                    print(f"  ✗ Erro ao buscar/criar pasto: {str(e)}")
                    erros.append(f"Linha {idx+1}: Erro ao processar pasto '{pasto_nome}' - {str(e)}")
                    continue
                
                # Criar o animal
                # Obter e converter os dados do animal
                try:
                    # Converter datas
                    data_nascimento = None
                    data_entrada = None
                    peso_entrada = None
                    valor_compra = None
                    
                    # Data de nascimento
                    if 'data de nascimento* (dd/mm/aaaa)' in row and not pd.isna(row['data de nascimento* (dd/mm/aaaa)']):
                        data_nasc = row['data de nascimento* (dd/mm/aaaa)']
                        if isinstance(data_nasc, (datetime, pd.Timestamp)):
                            data_nascimento = data_nasc.date()
                        else:
                            data_nascimento = pd.to_datetime(data_nasc).date()
                    else:
                        data_nascimento = timezone.now().date()  # Valor padrão
                    
                    # Data de entrada
                    if 'data de entrada* (dd/mm/aaaa)' in row and not pd.isna(row['data de entrada* (dd/mm/aaaa)']):
                        data_entr = row['data de entrada* (dd/mm/aaaa)']
                        if isinstance(data_entr, (datetime, pd.Timestamp)):
                            data_entrada = data_entr.date()
                        else:
                            data_entrada = pd.to_datetime(data_entr).date()
                    else:
                        data_entrada = timezone.now().date()  # Valor padrão
                    
                    # Peso de entrada
                    if 'peso de entrada (kg)*' in row and not pd.isna(row['peso de entrada (kg)*']):
                        peso_entrada = Decimal(str(row['peso de entrada (kg)*']))
                    else:
                        peso_entrada = Decimal('0.00')  # Valor padrão
                    
                    # Valor de compra
                    try:
                        if 'valor de compra (r$)*' in row and row['valor de compra (r$)*'] and not pd.isna(row['valor de compra (r$)*']) and str(row['valor de compra (r$)*']).strip():
                            # Limpa formatação de moeda e converte para Decimal
                            valor_raw = str(row['valor de compra (r$)*']).replace('R$', '').replace('.', '').replace(',', '.').strip()
                            if valor_raw:
                                valor_compra = Decimal(valor_raw)
                            else:
                                valor_compra = None  # Valor vazio
                        else:
                            valor_compra = None  # Valor ausente ou nulo
                    except (decimal.InvalidOperation, ValueError) as e:
                        print(f"  Aviso: Valor de compra inválido, definindo como nulo. Detalhe: {e}")
                        valor_compra = None  # Em caso de erro, define como nulo
                    
                    print(f"  Valores convertidos:\n    Data Nascimento: {data_nascimento}\n    Data Entrada: {data_entrada}\n    Peso: {peso_entrada}\n    Valor: {valor_compra}")
                    
                    # Tratar brinco eletrônico - usando NULL quando vazio
                    brinco_eletronico = None  # Garantir que comece como None (NULL no banco de dados)
                    
                    if 'brinco eletrônico' in row and not pd.isna(row['brinco eletrônico']):
                        brinco_eletronico_raw = str(row['brinco eletrônico']).strip()
                        if brinco_eletronico_raw:  # Se tiver conteúdo, usa o valor
                            brinco_eletronico = brinco_eletronico_raw
                    
                    print(f"    Brinco Eletrônico: {brinco_eletronico if brinco_eletronico else 'NULL'}")  
                    
                    # Criar o animal com os valores convertidos - sem incluir brinco_eletronico se for None
                    # Incluir data_atualizacao para evitar erro de not-null constraint
                    data_atual = timezone.now()
                    
                    animal_data = {
                        'brinco_visual': brinco_visual,
                        'lote': lote,
                        'raca': raca,
                        'categoria_animal': categoria,
                        'data_nascimento': data_nascimento,
                        'data_entrada': data_entrada,
                        'peso_entrada': peso_entrada,
                        'valor_compra': valor_compra,
                        'fazenda_atual': lote.fazenda,
                        'pasto_atual': pasto,
                        'situacao': 'ATIVO',
                        'usuario': request.user,
                        'data_atualizacao': data_atual
                    }
                    
                    # Adicionar brinco_eletronico apenas se tiver um valor
                    if brinco_eletronico:
                        animal_data['brinco_eletronico'] = brinco_eletronico
                    
                    # Criar o animal com os dados preparados
                    animal = Animal(**animal_data)
                except Exception as e:
                    print(f"  ✗ Erro ao preparar dados do animal: {str(e)}")
                    print(f"  Detalhe do erro: {traceback.format_exc()}")
                    erros.append(f"Linha {idx+1}: Erro ao preparar dados do animal '{brinco_visual}' - {str(e)}")
                    continue
                
                # NÃO PROCESSAR O BRINCO ELETRÔNICO NOVAMENTE - já foi tratado acima
                
                # Tentativa de salvar o animal com logs detalhados
                try:
                    print(f"  Tentando salvar animal com brinco: {animal.brinco_visual}")
                    print(f"  Dados do animal:\n    Lote: {animal.lote.id_lote}\n    Raça: {animal.raca.nome}\n    Categoria: {animal.categoria_animal.nome}\n    Data Nascimento: {animal.data_nascimento}\n    Data Entrada: {animal.data_entrada}\n    Peso: {animal.peso_entrada}\n    Fazenda: {animal.fazenda_atual.nome}\n    Pasto: {animal.pasto_atual.nome if animal.pasto_atual else 'Nenhum'}")
                    
                    # Verificar se estamos lidando com um animal sem brinco eletrônico
                    if not hasattr(animal, 'brinco_eletronico') or animal.brinco_eletronico is None:
                        # Usar SQL direto para inserir com brinco_eletronico NULL e contornar a restrição
                        from django.db import connection
                        
                        # Obter o próximo ID de animal
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT nextval('core_animal_id_seq')")
                            next_id = cursor.fetchone()[0]
                        
                        # Preparar valores para inserção
                        data_cadastro = timezone.now().strftime('%Y-%m-%d')
                        peso_entrada_str = str(animal.peso_entrada) if animal.peso_entrada else 'NULL'
                        valor_compra_str = str(animal.valor_compra) if animal.valor_compra else 'NULL'
                        pasto_id = f"'{animal.pasto_atual.id}'" if animal.pasto_atual else 'NULL'
                        
                        # Construir e executar a consulta SQL
                        with connection.cursor() as cursor:
                            # Obter data e hora atual para data_atualizacao
                            data_atualizacao = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            sql = f"""
                            INSERT INTO core_animal (
                                id, brinco_visual, brinco_eletronico, raca_id, data_nascimento, data_entrada,
                                lote_id, categoria_animal_id, peso_entrada, situacao, fazenda_atual_id,
                                pasto_atual_id, valor_compra, custo_fixo, custo_variavel, valor_total,
                                usuario_id, data_cadastro, data_atualizacao
                            ) VALUES (
                                {next_id}, '{animal.brinco_visual}', NULL, {animal.raca.id}, '{animal.data_nascimento}', '{animal.data_entrada}',
                                {animal.lote.id}, {animal.categoria_animal.id}, {peso_entrada_str}, 'ATIVO', {animal.fazenda_atual.id},
                                {pasto_id}, {valor_compra_str}, 0, 0, 0,
                                {animal.usuario.id}, '{data_cadastro}', '{data_atualizacao}'
                            )
                            """
                            print(f"  Executando SQL para inserção com brinco_eletronico NULL")
                            cursor.execute(sql)
                            
                        # Definir o ID do animal para logs
                        animal.id = next_id
                    else:
                        # Para animais com brinco eletrônico, salvar normalmente
                        animal.save()
                    
                    print(f"  ✓ Animal salvo com sucesso: {animal.brinco_visual} (ID: {animal.id})")
                    animais_importados += 1
                except Exception as e:
                    print(f"  ✗ Erro ao salvar animal: {str(e)}")
                    print(f"  Detalhe do erro: {traceback.format_exc()}")
                    erros.append(f"Linha {idx+1}: Erro ao salvar animal '{brinco_visual}' - {str(e)}")
                
            except Exception as e:
                erros.append(f"Linha {idx+1}: Erro ao processar - {str(e)}")
        
        # Log final dos resultados
        print(f"\n=== RESULTADO DA IMPORTAÇÃO ===")
        print(f"Total de animais processados: {len(df)}")
        print(f"Animais importados com sucesso: {animais_importados}")
        print(f"Erros encontrados: {len(erros)}")
        if erros:
            print("Lista de erros:")
            for e in erros:
                print(f" - {e}")
        
        # Preparar dados para o template de resumo
        status = 'success'
        message = f'Importação concluída com sucesso! {animais_importados} animais importados.'
        
        if animais_importados > 0:
            if erros:
                status = 'partial'
                message = f'Importação parcial: {animais_importados} animais importados com {len(erros)} erros.'
                messages.warning(request, message)
            else:
                messages.success(request, message)
        else:
            status = 'error'
            message = 'Nenhum animal foi importado. Verifique os erros e tente novamente.'
            messages.error(request, message)

        # Renderizar o template de resultado em vez de retornar JSON
        context = {
            'status': status,
            'message': message,
            'animais_importados': animais_importados,
            'total_processados': len(df),
            'erros': erros,
        }
        return render(request, 'animais/import_resultado.html', context)
                
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao processar arquivo: {str(e)}'
        })
