"""
Instruções para corrigir o erro "Cannot resolve keyword 'fazenda_id' into field"

O erro está ocorrendo porque o código está tentando filtrar o modelo Despesa pelo campo
'fazenda_id', mas esse campo não existe diretamente no modelo. Em vez disso, a relação
com a fazenda é feita através do campo 'itens__fazenda_destino_id'.

Para corrigir o problema, siga estas instruções:

1. Abra o arquivo views_dashboard_simples.py

2. Localize todas as ocorrências onde o código está tentando filtrar despesas por fazenda_id.
   Normalmente, essas ocorrências seguem este padrão:
   
   ```python
   despesas = despesas.filter(**filtro_fazenda)
   ```
   
   ou
   
   ```python
   filtro_fazenda = {'fazenda_id': fazenda_id}
   ```

3. Substitua essas ocorrências pelo código correto:
   
   ```python
   despesas = despesas.filter(itens__fazenda_destino_id=fazenda_id).distinct()
   ```
   
   ou
   
   ```python
   filtro_fazenda = {'itens__fazenda_destino_id': fazenda_id}
   ```

4. Certifique-se de adicionar .distinct() após o filtro para evitar duplicatas.

5. Salve o arquivo e reinicie o servidor.

Funções que precisam ser corrigidas:
- obter_dados_financeiros
- obter_entradas_saidas_12_meses
- obter_categorias_custo
- obter_contas_a_pagar

Exemplo de correção para obter_categorias_custo:

Antes:
```python
if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
    despesas = despesas.filter(**filtro_fazenda)
```

Depois:
```python
if fazenda_id and fazenda_id != 'null' and fazenda_id != '':
    # Usar itens__fazenda_destino_id em vez de fazenda_id
    despesas = despesas.filter(itens__fazenda_destino_id=fazenda_id).distinct()
```
"""
