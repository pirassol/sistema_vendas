# Instalação do Sistema de Vendas com Docker e Traefik

Este guia explica como instalar o Sistema de Vendas usando Docker Compose com Traefik como proxy reverso.

## Pré-requisitos

- Docker instalado
- Docker Compose instalado
- Traefik já instalado e configurado
- Domínio configurado: festeja.ciadaweb.com.br
- Rede Docker "festeja" criada

## Instalação

1. Crie um diretório para o projeto e entre nele:
```bash
mkdir sistema_vendas
cd sistema_vendas
```

2. Crie a rede Docker (caso ainda não exista):
```bash
docker network create festeja
```

3. Crie o arquivo docker-compose.yml com o conteúdo fornecido

4. Inicie o sistema:
```bash
docker-compose up -d
```

O Docker irá:
- Baixar o código diretamente do GitHub
- Construir a imagem usando o Dockerfile do repositório
- Configurar os volumes e redes necessários
- Iniciar o container

## Acesso

- Sistema de Vendas: https://festeja.ciadaweb.com.br

## Manutenção

- Para ver os logs:
```bash
docker-compose logs -f
```

- Para parar o container:
```bash
docker-compose down
```

- Para atualizar:
```bash
docker-compose down
docker-compose up -d --build
```

## Backup

O diretório `instance` contém o banco de dados SQLite. Faça backup regular deste diretório:

```bash
tar -czf backup_$(date +%Y%m%d).tar.gz instance/
```

## Segurança

- O sistema está configurado para usar HTTPS através do Traefik
- Certificados SSL são gerenciados automaticamente pelo Let's Encrypt 