import requests

url = "https://api-prod.eduzz.com/api/1.1/sale/get_sale_list"
headers = {
    'publickey': '10434573',
    'apikey': '4a2a8c627751ced4e0dfeb197d6aa10224ab8e97cb696c24109f931d160736ec',
    'Content-Type': 'application/json'
}

try:
    print("Fazendo requisição para a Eduzz...")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    
    response = requests.get(url, headers=headers, verify=False)  # Desabilitando verificação SSL para teste
    
    print(f"\nStatus code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Erro: {str(e)}")
