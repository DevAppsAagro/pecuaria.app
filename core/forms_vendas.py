from django import forms
from django.core.exceptions import ValidationError
from .models_vendas import Venda
from .models import Contato, ContaBancaria
from django.utils import timezone

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
        
        # Define valores padrão para as datas
        if not self.instance.pk:  # Se for uma nova venda
            hoje = timezone.localdate()
            self.fields['data'].initial = hoje
            self.fields['data_vencimento'].initial = hoje
        
        if usuario:
            # Filtra apenas contatos do tipo CO (Comprador)
            self.fields['comprador'].queryset = Contato.objects.filter(
                usuario=usuario,
                tipo='CO'
            )
            
            # Filtra as contas bancárias pelo usuário
            self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(
                usuario=usuario,
                ativa=True
            )
        
        # Adiciona mensagens se não houver registros
        if not self.fields['comprador'].queryset.exists():
            self.fields['comprador'].empty_label = "Nenhum comprador cadastrado"
        if not self.fields['conta_bancaria'].queryset.exists():
            self.fields['conta_bancaria'].empty_label = "Nenhuma conta bancária cadastrada"

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        data_vencimento = cleaned_data.get('data_vencimento')
        data_pagamento = cleaned_data.get('data_pagamento')
        valor_unitario = cleaned_data.get('valor_unitario')
        numero_parcelas = cleaned_data.get('numero_parcelas')

        # Se não tiver data, usa hoje
        if not data:
            data = timezone.localdate()
            cleaned_data['data'] = data

        # Se não tiver data de vencimento, usa hoje
        if not data_vencimento:
            data_vencimento = timezone.localdate()
            cleaned_data['data_vencimento'] = data_vencimento

        if data and data > timezone.localdate():
            raise ValidationError('A data da venda não pode ser futura.')

        if data_vencimento and data and data_vencimento < data:
            raise ValidationError('A data de vencimento não pode ser anterior à data da venda.')

        if data_pagamento:
            if data and data_pagamento < data:
                raise ValidationError('A data de pagamento não pode ser anterior à data da venda.')
            if data_pagamento > timezone.localdate():
                raise ValidationError('A data de pagamento não pode ser futura.')

        if valor_unitario and valor_unitario <= 0:
            raise ValidationError('O valor unitário deve ser maior que zero.')

        if numero_parcelas and numero_parcelas < 1:
            raise ValidationError('O número de parcelas deve ser maior que zero.')

        return cleaned_data
