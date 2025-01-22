from pyngrok import ngrok
import os
import sys
import subprocess

def run_server_with_ngrok():
    # Configura o token do ngrok
    ngrok.set_auth_token("2q2k4ufo6KC4l07AtSbywHcEVAC_6GXrijDDLJ5tXhtWJ1q7M")
    
    # Inicia o túnel ngrok
    http_tunnel = ngrok.connect(8000)
    print(f'\nURL pública do ngrok: {http_tunnel.public_url}')
    print('Configure esta URL + /webhook/eduzz/ no seu painel da Eduzz')
    print(f'Exemplo: {http_tunnel.public_url}/webhook/eduzz/')
    print('\nPressione Ctrl+C para encerrar\n')

    # Inicia o servidor Django
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver'])
    except KeyboardInterrupt:
        print('\nEncerrando servidor...')
    finally:
        # Fecha o túnel ngrok
        ngrok.kill()

if __name__ == '__main__':
    run_server_with_ngrok()
