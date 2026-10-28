# Etapa 1: instala as dependências Python num venv
FROM python:3.11.5-slim-bookworm AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


# Etapa 2: imagem final, só com o venv pronto e o código
FROM python:3.11.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Bibliotecas do sistema que o WeasyPrint usa para gerar PDF
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app

WORKDIR /app
RUN chown app:app /app

COPY --from=build /opt/venv /opt/venv
COPY --chown=app:app . .

USER app

# collectstatic só copia arquivos: valores falsos bastam aqui (não ficam na imagem)
RUN SECRET_KEY=build ENVIRONMENT=PROD python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "scripts/start.sh"]
