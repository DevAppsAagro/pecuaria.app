import re

# Caminho para o arquivo views.py
views_file_path = 'core/views.py'

# Ler o conteúdo atual do arquivo
with open(views_file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Atualizar a primeira implementação de DespesaCreateView
first_despesa_create_pattern = r'def form_valid\(self, form\):\s+try:\s+with transaction\.atomic\(\):\s+# Salva a despesa\s+self\.object = form\.save\(commit=False\)\s+self\.object\.usuario = self\.request\.user\s+\s+# Define o status baseado na data de pagamento\s+if self\.object\.data_pagamento:\s+self\.object\.status = \'PAGO\'\s+\s+self\.object\.save\(\)'

first_despesa_create_replacement = """def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva a despesa
                self.object = form.save(commit=False)
                self.object.usuario = self.request.user
                
                # Define o status baseado na data de pagamento
                if self.object.data_pagamento:
                    self.object.status = 'PAGO'
                
                # Processa os arquivos de comprovante e boleto
                from .supabase_utils import process_despesa_files
                self.object = process_despesa_files(form, self.object, self.request)
                
                self.object.save()"""

content = re.sub(first_despesa_create_pattern, first_despesa_create_replacement, content)

# Atualizar a segunda implementação de DespesaCreateView
second_despesa_create_pattern = r'def form_valid\(self, form\):\s+try:\s+with transaction\.atomic\(\):\s+# Salva a despesa\s+self\.object = form\.save\(commit=False\)\s+self\.object\.usuario = self\.request\.user\s+\s+# Define o status baseado na data de pagamento\s+if self\.object\.data_pagamento:\s+self\.object\.status = \'PAGO\'\s+\s+self\.object\.save\(\)'

second_despesa_create_replacement = """def form_valid(self, form):
        try:
            with transaction.atomic():
                # Salva a despesa
                self.object = form.save(commit=False)
                self.object.usuario = self.request.user
                
                # Define o status baseado na data de pagamento
                if self.object.data_pagamento:
                    self.object.status = 'PAGO'
                
                # Processa os arquivos de comprovante e boleto
                from .supabase_utils import process_despesa_files
                self.object = process_despesa_files(form, self.object, self.request)
                
                self.object.save()"""

content = re.sub(second_despesa_create_pattern, second_despesa_create_replacement, content, count=1)

# Atualizar a implementação de DespesaUpdateView
despesa_update_pattern = r'def form_valid\(self, form\):'

despesa_update_replacement = """def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                
                # Processa os arquivos de comprovante e boleto
                from .supabase_utils import process_despesa_files
                self.object = process_despesa_files(form, self.object, self.request)
                
                self.object.save()
                return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Erro ao atualizar despesa: {str(e)}")
            return self.form_invalid(form)"""

# Encontrar a posição da classe DespesaUpdateView
despesa_update_class_pos = content.find("class DespesaUpdateView(LoginRequiredMixin, UpdateView):")
if despesa_update_class_pos != -1:
    # Encontrar a posição do método form_valid dentro da classe
    form_valid_pos = content.find("def form_valid(self, form):", despesa_update_class_pos)
    if form_valid_pos != -1:
        # Encontrar o final do método form_valid
        next_def_pos = content.find("def ", form_valid_pos + 1)
        if next_def_pos != -1:
            # Substituir todo o método form_valid
            content = content[:form_valid_pos] + despesa_update_replacement + content[next_def_pos:]
        else:
            # Se não encontrar o próximo método, substituir até o final da classe
            next_class_pos = content.find("class ", form_valid_pos + 1)
            if next_class_pos != -1:
                content = content[:form_valid_pos] + despesa_update_replacement + content[next_class_pos:]

# Salvar o conteúdo atualizado
with open(views_file_path, 'w', encoding='utf-8') as file:
    file.write(content)

print("Arquivo views.py atualizado com sucesso!")
