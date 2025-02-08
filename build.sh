#!/bin/bash

# Instala as dependências
pip install -r requirements.txt

# Coleta arquivos estáticos
python3.9 manage.py collectstatic --noinput

# Aplica as migrações
python manage.py migrate
