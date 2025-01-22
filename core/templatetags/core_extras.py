from django import template
from decimal import Decimal
from datetime import timedelta

register = template.Library()

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
def add_days(value, days):
    """Adiciona um número de dias a uma data"""
    return value + timedelta(days=int(days))
