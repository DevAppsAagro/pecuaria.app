from django import forms
from .models_vendas import Venda
from .models import Contato

class VendaForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = [
            'data',
            'data_vencimento',
            'data_pagamento',
            'tipo_venda',
            'valor_unitario',
            'comprador',
            'conta_bancaria',
            'numero_parcelas',
            'intervalo_parcelas'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_venda': forms.Select(attrs={'class': 'form-control'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'comprador': forms.Select(attrs={'class': 'form-control'}),
            'conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'intervalo_parcelas': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        # Filtra apenas contatos do tipo CO (Comprador)
        self.fields['comprador'].queryset = Contato.objects.filter(
            usuario=usuario if not self.instance.pk else self.instance.usuario,
            tipo='CO'
        )
