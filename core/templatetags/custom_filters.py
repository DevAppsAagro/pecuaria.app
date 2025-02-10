from django import template
from decimal import Decimal
from datetime import timedelta

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtrai o argumento do valor"""
    try:
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide o valor pelo argumento"""
    try:
        if not arg or float(arg) == 0:
            return None
        return float(value or 0) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return None

@register.filter
def add_days(value, days):
    """Adiciona dias a uma data"""
    try:
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return Decimal(str(value)) / Decimal(str(arg))
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def add_class(field, css_class):
    """Adiciona uma classe CSS a um campo de formulário"""
    return field.as_widget(attrs={'class': css_class})

@register.filter
def sum_attr(queryset, attr_name):
    """Soma os valores de um atributo em um queryset"""
    try:
        return sum(Decimal(str(getattr(obj, attr_name))) for obj in queryset)
    except (ValueError, TypeError, AttributeError):
        return Decimal('0')

@register.filter
def dias_entre(data_final, data_inicial):
    """Calcula o número de dias entre duas datas"""
    if not data_final or not data_inicial:
        return 0
    # Garante que o resultado seja sempre positivo usando abs()
    return abs((data_final - data_inicial).days)

@register.filter
def sub(valor1, valor2):
    """Subtrai dois valores"""
    try:
        return float(valor1) - float(valor2)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(valor1, valor2):
    """Divide dois valores"""
    try:
        valor2 = float(valor2)
        if valor2 == 0:
            return 0
        return float(valor1) / valor2
    except (ValueError, TypeError):
        return 0

@register.filter
def previous(lista, indice):
    """Retorna o item anterior de uma lista"""
    try:
        return lista[int(indice) - 1]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def next(lista, indice):
    """Retorna o próximo item de uma lista"""
    try:
        return lista[int(indice) + 1]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def format_decimal_br(value):
    """Formata um número decimal no padrão brasileiro (1.234,56)"""
    try:
        # Converte para string com 2 casas decimais
        value = f"{float(value):.2f}"
        # Separa parte inteira e decimal
        int_part, dec_part = value.split('.')
        # Adiciona pontos a cada 3 dígitos da parte inteira
        int_part = '.'.join([int_part[max(i-3, 0):i] for i in range(len(int_part), 0, -3)][::-1])
        # Junta com vírgula
        return f"{int_part},{dec_part}"
    except (ValueError, TypeError, AttributeError):
        return value

@register.filter
def format_currency_br(value):
    """Formata um valor monetário no padrão brasileiro (R$ 1.234,56)"""
    try:
        return f"R$ {format_decimal_br(value)}"
    except (ValueError, TypeError, AttributeError):
        return value

@register.filter
def get_item(dictionary, key):
    """Retorna um item do dicionário pela chave"""
    return dictionary.get(key)

@register.filter
def format_status(value):
    status_map = {
        'PAGO': 'Pago',
        'PENDENTE': 'Pendente',
        'VENCIDO': 'Vencido',
        'VENCE_HOJE': 'Vence Hoje',
        'CANCELADO': 'Cancelado'
    }
    return status_map.get(value, value)
