class DespesaCreateView(LoginRequiredMixin, CreateView):
    model = Despesa
    template_name = 'financeiro/despesa_form.html'
    success_url = reverse_lazy('despesas_list')
    fields = ['forma_pagamento', 'numero_nf', 'data_emissao', 'data_vencimento', 'data_pagamento', 'contato', 'arquivo', 'boleto', 'conta_bancaria']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaCusto.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['unidades'] = UnidadeMedida.objects.filter(Q(usuario=self.request.user) | Q(usuario__isnull=True))
        context['contatos'] = Contato.objects.filter(usuario=self.request.user, tipo='FO')
        context['contas_bancarias'] = ContaBancaria.objects.filter(usuario=self.request.user, ativa=True)
        return context

    def form_valid(self, form):
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
                
                self.object.save()

                # Processa os itens da despesa
                itens_data = json.loads(self.request.POST.get('itens_despesa', '[]'))
                for item_data in itens_data:
                    categoria = CategoriaCusto.objects.get(
                        Q(id=item_data['categoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    subcategoria = SubcategoriaCusto.objects.get(
                        Q(id=item_data['subcategoria_id']) & (Q(usuario=self.request.user) | Q(usuario__isnull=True))
                    )
                    
                    # Cria o item da despesa
                    item_despesa = ItemDespesa(
                        despesa=self.object,
                        categoria=categoria,
                        subcategoria=subcategoria,
                        quantidade=item_data['quantidade'],
                        valor_unitario=item_data['valor_unitario'],
                        unidade_medida=UnidadeMedida.objects.get(id=item_data['unidade_id']) if item_data.get('unidade_id') else None,
                        descricao=item_data.get('descricao', '')
                    )
                    item_despesa.save()
                    
                    # Processa o rateio de custos
                    rateios_data = item_data.get('rateios', [])
                    for rateio_data in rateios_data:
                        if rateio_data.get('fazenda_id') and rateio_data.get('percentual'):
                            fazenda = Fazenda.objects.get(id=rateio_data['fazenda_id'], usuario=self.request.user)
                            rateio = RateioCusto(
                                item_despesa=item_despesa,
                                fazenda=fazenda,
                                percentual=rateio_data['percentual']
                            )
                            rateio.save()
                
                # Processa as parcelas da despesa
                if self.object.forma_pagamento == 'PR':
                    parcelas_data = json.loads(self.request.POST.get('parcelas_despesa', '[]'))
                    for parcela_data in parcelas_data:
                        parcela = ParcelaDespesa(
                            despesa=self.object,
                            numero=parcela_data['numero'],
                            data_vencimento=datetime.strptime(parcela_data['data_vencimento'], '%Y-%m-%d').date(),
                            valor=parcela_data['valor'],
                            status='PAGO' if parcela_data.get('pago') else 'PENDENTE'
                        )
                        parcela.save()
                
                return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Erro ao salvar despesa: {str(e)}")
            return self.form_invalid(form)
