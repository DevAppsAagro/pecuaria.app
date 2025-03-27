"""
Este arquivo contém a correção para a função animal_detail
para exibir os dados reprodutivos na página de detalhes do animal.

Para aplicar a correção, modifique a função animal_detail no arquivo views.py
adicionando o código abaixo antes da criação do contexto (linha ~4012):

# Busca informações reprodutivas
manejos_reprodutivos = ManejoReproducao.objects.filter(animal=animal).order_by('-data_concepcao')

# Busca bezerros (filhos) para fêmeas
filhos = None
bezerros_organizados = []
if animal.sexo == 'F':  # Se for fêmea
    filhos = Animal.objects.filter(mae=animal)
    
    # Organiza bezerros por estação de monta
    if filhos.exists():
        # Agrupa bezerros por estação de monta
        bezerros_por_estacao = {}
        for filho in filhos:
            # Tenta encontrar o manejo reprodutivo que resultou neste bezerro
            manejo = ManejoReproducao.objects.filter(
                animal=animal,
                data_resultado=filho.data_nascimento,
                resultado='NASCIMENTO'
            ).first()
            
            estacao = manejo.estacao_monta if manejo else None
            
            if estacao not in bezerros_por_estacao:
                bezerros_por_estacao[estacao] = []
            
            bezerros_por_estacao[estacao].append(filho)
        
        # Converte o dicionário para uma lista de tuplas (estacao, bezerros)
        bezerros_organizados = [(estacao, bezerros) for estacao, bezerros in bezerros_por_estacao.items()]

# Busca informações sobre a estação de monta de origem (se for bezerro)
estacao_origem = None
if animal.data_nascimento and animal.mae:
    # Tenta encontrar o manejo reprodutivo que resultou neste animal
    estacao_origem = ManejoReproducao.objects.filter(
        animal=animal.mae,
        data_resultado=animal.data_nascimento,
        resultado='NASCIMENTO'
    ).first()
    
    if estacao_origem:
        estacao_origem = estacao_origem.estacao_monta

E adicione estas variáveis ao contexto (linha ~4040):

'manejos_reprodutivos': manejos_reprodutivos,
'filhos': filhos,
'bezerros_organizados': bezerros_organizados,
'estacao_origem': estacao_origem,
"""
