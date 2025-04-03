"""
Script para aplicar correções no arquivo views_dashboard_simples.py
"""
import re
import os

def aplicar_correcoes():
    # Caminho do arquivo
    arquivo_original = os.path.join(os.path.dirname(__file__), 'views_dashboard_simples.py')
    arquivo_backup = os.path.join(os.path.dirname(__file__), 'views_dashboard_simples_backup.py')
    
    # Criar backup do arquivo original
    with open(arquivo_original, 'r', encoding='utf-8') as f:
        conteudo_original = f.read()
    
    with open(arquivo_backup, 'w', encoding='utf-8') as f:
        f.write(conteudo_original)
    
    print(f"Backup criado em {arquivo_backup}")
    
    # Aplicar correções
    conteudo_corrigido = conteudo_original
    
    # 1. Corrigir 'valor_pago' para 'valor_final()'
    conteudo_corrigido = re.sub(r'despesa\.valor_pago', 'despesa.valor_final()', conteudo_corrigido)
    
    # 2. Corrigir 'pago=False' para 'status='PENDENTE''
    conteudo_corrigido = re.sub(r'pago\s*=\s*False', "status='PENDENTE'", conteudo_corrigido)
    conteudo_corrigido = re.sub(r'pago\s*=\s*True', "status='PAGO'", conteudo_corrigido)
    
    # 3. Corrigir 'data_abate' para 'data'
    conteudo_corrigido = re.sub(r'data_abate', 'data', conteudo_corrigido)
    
    # 4. Garantir que todos os pastos sejam incluídos (sem filtros adicionais)
    # Isso é mais complexo e pode precisar de ajustes manuais
    
    # Salvar o arquivo corrigido
    with open(arquivo_original, 'w', encoding='utf-8') as f:
        f.write(conteudo_corrigido)
    
    print(f"Correções aplicadas em {arquivo_original}")
    print("Verifique se todas as correções foram aplicadas corretamente.")
    print("Caso necessário, restaure o backup manualmente.")

if __name__ == "__main__":
    aplicar_correcoes()
