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

# Criar diretórios necessários e ajustar permissões iniciais
RUN mkdir -p /app/static/uploads \
    && mkdir -p /app/instance \
    && mkdir -p /app/templates \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app \
    && chmod -R 777 /app/static/uploads \
    && chmod -R 777 /app/instance \
    && chmod -R 777 /app/templates

# Copiar arquivos da aplicação
COPY --chown=appuser:appuser . .

# Garantir que os diretórios mantenham as permissões corretas após a cópia
RUN chmod -R 755 /app \
    && chmod -R 777 /app/static/uploads \
    && chmod -R 777 /app/instance \
    && chmod -R 777 /app/templates

USER appuser

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"] 