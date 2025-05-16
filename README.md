# Sistema de Vendas

Sistema de gerenciamento de vendas desenvolvido em Python com Flask.

## Requisitos

- Python 3.9+
- Docker (opcional)

## Instalação

### Usando Docker

```bash
# Construir a imagem
docker build -t sistema-vendas .

# Executar o container
docker run -p 5000:5000 sistema-vendas
```

### Instalação Local

1. Clone o repositório
2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
flask run
```

## Estrutura do Projeto

- `app.py`: Arquivo principal da aplicação
- `static/`: Arquivos estáticos (CSS, JS, imagens)
- `templates/`: Templates HTML
- `instance/`: Arquivos de configuração local
- `static/uploads/`: Diretório para upload de imagens

## Licença

Este projeto está sob a licença MIT. 