import sqlite3

def init_db():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    # Criar tabela de empresas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT UNIQUE NOT NULL,
        cep TEXT NOT NULL,
        endereco TEXT NOT NULL,
        numero TEXT NOT NULL,
        complemento TEXT,
        bairro TEXT NOT NULL,
        cidade TEXT NOT NULL,
        estado TEXT NOT NULL,
        status TEXT DEFAULT 'pendente',
        ativo BOOLEAN DEFAULT TRUE,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Criar tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'vendedor',
        empresa_id INTEGER NOT NULL,
        ativo BOOLEAN DEFAULT TRUE,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        reset_token TEXT,
        reset_token_expira DATETIME,
        foto TEXT,
        FOREIGN KEY (empresa_id) REFERENCES empresa (id)
    )
    ''')
    
    # Criar tabela de eventos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS evento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        data_inicio DATETIME NOT NULL,
        data_fim DATETIME NOT NULL,
        status TEXT DEFAULT 'ativo',
        FOREIGN KEY (empresa_id) REFERENCES empresa (id)
    )
    ''')
    
    # Criar tabela de barracas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS barraca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        descricao TEXT,
        evento_id INTEGER NOT NULL,
        FOREIGN KEY (empresa_id) REFERENCES empresa (id),
        FOREIGN KEY (evento_id) REFERENCES evento (id)
    )
    ''')
    
    # Criar tabela de produtos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS produto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        preco REAL NOT NULL,
        quantidade INTEGER NOT NULL,
        estoque_minimo INTEGER NOT NULL DEFAULT 5,
        foto TEXT,
        evento_id INTEGER NOT NULL,
        barraca_id INTEGER NOT NULL,
        FOREIGN KEY (empresa_id) REFERENCES empresa (id),
        FOREIGN KEY (evento_id) REFERENCES evento (id),
        FOREIGN KEY (barraca_id) REFERENCES barraca (id)
    )
    ''')
    
    # Criar tabela de vendas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        evento_id INTEGER NOT NULL,
        data_venda DATETIME NOT NULL,
        status TEXT NOT NULL DEFAULT 'concluido',
        total REAL NOT NULL DEFAULT 0.0,
        cancelada BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (empresa_id) REFERENCES empresa (id),
        FOREIGN KEY (usuario_id) REFERENCES usuario (id),
        FOREIGN KEY (evento_id) REFERENCES evento (id)
    )
    ''')
    
    # Criar tabela de itens de venda
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS item_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL,
        status TEXT DEFAULT 'pago',
        FOREIGN KEY (venda_id) REFERENCES venda (id),
        FOREIGN KEY (produto_id) REFERENCES produto (id)
    )
    ''')
    
    # Criar tabela de pagamentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pagamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL,
        forma_pagamento TEXT NOT NULL,
        valor REAL NOT NULL,
        valor_recebido REAL,
        troco REAL,
        FOREIGN KEY (venda_id) REFERENCES venda (id)
    )
    ''')
    
    # Criar tabela de configurações
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_sistema TEXT NOT NULL,
        descricao_sistema TEXT,
        cor_primaria TEXT,
        cor_secundaria TEXT,
        cor_menu TEXT,
        cor_rodape TEXT,
        mostrar_rodape BOOLEAN DEFAULT TRUE,
        texto_rodape TEXT,
        favicon_path TEXT,
        favicon_version INTEGER DEFAULT 1
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Banco de dados inicializado com sucesso!') 