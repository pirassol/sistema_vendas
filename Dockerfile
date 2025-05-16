FROM python:3.9-slim

WORKDIR /app

# Criar usuário não-root com UID 1000
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar script de inicialização
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Criar diretórios necessários\n\
mkdir -p /app/static/uploads\n\
mkdir -p /app/instance\n\
mkdir -p /app/templates\n\
\n\
# Ajustar permissões\n\
chown -R appuser:appuser /app\n\
chmod -R 755 /app\n\
chmod -R 777 /app/static/uploads\n\
chmod -R 777 /app/instance\n\
chmod -R 777 /app/templates\n\
\n\
# Executar como appuser\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Copiar arquivos da aplicação
COPY --chown=appuser:appuser . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PYTHONUNBUFFERED=1

# Executar como root para garantir que o script de inicialização tenha permissões
CMD ["/app/entrypoint.sh"] 