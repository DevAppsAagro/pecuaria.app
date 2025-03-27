# Script para corrigir o erro de sintaxe no arquivo views.py
with open('core/views.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Corrigir o erro de sintaxe adicionando uma quebra de linha
error_pattern = "return self.form_invalid(form)def get_queryset"
fixed_pattern = "return self.form_invalid(form)\n\n    def get_queryset"

corrected_content = content.replace(error_pattern, fixed_pattern)

with open('core/views.py', 'w', encoding='utf-8') as file:
    file.write(corrected_content)

print("Erro de sintaxe corrigido com sucesso!")
