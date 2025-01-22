from django import forms
from django.db.models import Q
from .models_compras import Compra
from .models import Animal, Contato, ContaBancaria

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = [
            'data',
            'data_vencimento',
            'data_pagamento',
            'tipo_compra',
            'valor_unitario',
            'vendedor',
            'conta_bancaria',
            'numero_parcelas',
            'intervalo_parcelas'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_compra': forms.Select(attrs={'class': 'form-control'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'vendedor': forms.Select(attrs={'class': 'form-control'}),
            'conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'intervalo_parcelas': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtra apenas contatos do tipo FO (Fornecedor)
        self.fields['vendedor'].queryset = Contato.objects.filter(
            usuario=user if not self.instance.pk else self.instance.usuario,
            tipo='FO'
        )
        
        # Filtra apenas contas ativas
        self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(
            usuario=user if not self.instance.pk else self.instance.usuario,
            ativa=True
        )
