#!/bin/sh
# Aplica as migrations e sobe o servidor (mesmo comando do conf/jiifs.service)
set -e

python manage.py migrate --noinput

exec gunicorn interclasse.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000
