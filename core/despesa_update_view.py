class DespesaUpdateView(LoginRequiredMixin, UpdateView):
    model = Despesa
    template_name = 'financeiro/despesa_form.html'
    fields = ['numero_nf', 'data_emissao', 'data_vencimento', 'contato', 'forma_pagamento', 'arquivo', 'boleto']
    success_url = reverse_lazy('despesas_list')

    def get_queryset(self):
        return Despesa.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
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
            return self.form_invalid(form)
