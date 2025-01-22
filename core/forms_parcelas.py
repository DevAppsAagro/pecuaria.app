from django import forms
from .models_parcelas import PagamentoParcela
from .models import ContaBancaria

class PagamentoParcelaForm(forms.ModelForm):
    class Meta:
        model = PagamentoParcela
        fields = ['data_pagamento', 'valor', 'conta_bancaria', 'observacao']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, parcela=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parcela = parcela
        if parcela:
            # Filtra contas bancárias pelo usuário da compra
            self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(
                usuario=parcela.compra.usuario,
                ativa=True
            )
            self.fields['valor'].initial = parcela.valor_restante
            self.fields['valor'].widget.attrs['max'] = parcela.valor_restante
