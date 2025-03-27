"""
Correção para a exibição dos bezerros no template animal_detail.html

O problema está na forma como os bezerros são organizados no código Python e como são acessados no template.

Na função animal_detail, modifique a linha:
bezerros_organizados = [(estacao, bezerros) for estacao, bezerros in bezerros_por_estacao.items()]

Para:
bezerros_organizados = [{'estacao': estacao, 'bezerros': bezerros} for estacao, bezerros in bezerros_por_estacao.items()]

Isso criará uma lista de dicionários em vez de tuplas, permitindo que o template acesse os dados corretamente.
"""
