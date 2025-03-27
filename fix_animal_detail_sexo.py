"""
Correção para o erro 'Animal' object has no attribute 'sexo'

O problema ocorre porque estamos tentando acessar animal.sexo, mas o sexo do animal
é determinado pela categoria do animal, não é um atributo direto do animal.

Substitua a linha:
if animal.sexo == 'F':  # Se for fêmea

Por:
if animal.categoria_animal.sexo == 'F':  # Se for fêmea
"""
