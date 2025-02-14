from django import forms
from .models import MovimentacaoNaoOperacional
from .models_abates import Abate

class MovimentacaoNaoOperacionalForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoNaoOperacional
        fields = ['data', 'data_vencimento', 'data_pagamento', 'tipo', 
                 'conta_bancaria', 'fazenda', 'valor', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['fazenda'].queryset = user.fazenda_set.all()
            self.fields['conta_bancaria'].queryset = user.contabancaria_set.all()
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class AbateForm(forms.ModelForm):
    class Meta:
        model = Abate
        fields = ['data', 'data_vencimento', 'data_pagamento', 'valor_arroba', 'rendimento_padrao',
                 'conta_bancaria', 'comprador']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'valor_arroba': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rendimento_padrao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'comprador': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        if usuario:
            # Filtra as contas bancárias pelo usuário
            self.fields['conta_bancaria'].queryset = usuario.contabancaria_set.all()
            # Filtra os compradores pelo usuário e tipo CO
            self.fields['comprador'].queryset = usuario.contato_set.filter(tipo='CO').order_by('nome')
            # Adiciona mensagem se não houver compradores
            if not self.fields['comprador'].queryset.exists():
                self.fields['comprador'].empty_label = "Nenhum comprador cadastrado"
            
        # Adiciona um valor padrão para o rendimento
        if not self.instance.pk:  # Se for um novo abate
            self.fields['rendimento_padrao'].initial = 54.00  # 54% como padrão
