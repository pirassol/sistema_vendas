# Sistema de Vendas com Geração de Fichas

Este é um sistema de vendas que permite cadastrar produtos e gerar fichas individuais para cada venda, que podem ser retiradas nas barracas.

## Funcionalidades

- Cadastro de produtos com nome, preço e quantidade
- Registro de vendas
- Geração automática de fichas em PDF para cada venda
- Interface web amigável
- Controle de estoque automático

## Requisitos

- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Navegue até a pasta do projeto
3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Usar

1. Inicie o servidor:
```bash
python app.py
```

2. Abra seu navegador e acesse:
```
http://localhost:5000
```

3. Use o sistema:
   - Cadastre produtos na página inicial
   - Realize vendas selecionando o produto e informando a barraca
   - As fichas serão geradas automaticamente após cada venda

## Estrutura do Projeto

- `app.py`: Arquivo principal da aplicação
- `templates/`: Pasta com os templates HTML
- `vendas.db`: Banco de dados SQLite (criado automaticamente)
- `requirements.txt`: Lista de dependências do projeto

## Tecnologias Utilizadas

- Flask: Framework web
- SQLAlchemy: ORM para banco de dados
- ReportLab: Geração de PDFs
- Bootstrap: Framework CSS para interface 