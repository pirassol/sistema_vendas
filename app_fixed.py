from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
from werkzeug.utils import secure_filename
import json
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from flask_mail import Message, Mail
import qrcode
import io
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vendas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua_chave_secreta_muito_forte_aqui'

# Configuração do upload de arquivos
UPLOAD_FOLDER = os.path.join('static', 'uploads')
FOTOS_PRODUTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_produtos')
FOTOS_EVENTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_eventos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FOTOS_PRODUTOS_FOLDER'] = FOTOS_PRODUTOS_FOLDER
app.config['FOTOS_EVENTOS_FOLDER'] = FOTOS_EVENTOS_FOLDER

# Criar diretórios se não existirem
os.makedirs(FOTOS_PRODUTOS_FOLDER, exist_ok=True)
os.makedirs(FOTOS_EVENTOS_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Configuração Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

# Configurações padrão do sistema
DEFAULT_CONFIG = {
    'nome_sistema': 'Festeja',
    'descricao_sistema': 'Sistema de Gestão de Vendas para Eventos',
    'exibir_rodape': True,
    'texto_rodape': 'Todos os direitos reservados',
    'cor_menu': '#0d6efd',
    'cor_rodape': '#212529',
    'cor_primaria': '#0d6efd',
    'cor_secundaria': '#6c757d'
}

# Caminho para o arquivo de configurações
CONFIG_FILE = os.path.join('static', 'config.json')

# Configuração de e-mail
app.config['MAIL_SERVER'] = 'smtp.hostinger.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'caio.pirassol@ciadaweb.com.br'
app.config['MAIL_PASSWORD'] = 'D499022d.'
app.config['MAIL_DEFAULT_SENDER'] = 'caio.pirassol@ciadaweb.com.br'

mail = Mail(app)

def allowed_file(filename, allowed_extensions=None):
    """Verifica se a extensão do arquivo é permitida"""
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def load_config():
    """Carrega as configurações do sistema do arquivo JSON"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Verificar se o favicon existe
                if 'favicon_path' in config:
                    favicon_path = os.path.join(app.static_folder, config['favicon_path'])
                    if not os.path.exists(favicon_path):
                        # Se o favicon não existir, remover a referência
                        del config['favicon_path']
                
                return config
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")
    
    # Se o arquivo não existir ou houver erro, retorna as configurações padrão
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Salva as configurações do sistema em um arquivo JSON"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")
        return False

class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    cep = db.Column(db.String(8), nullable=False)
    endereco = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuarios = db.relationship('Usuario', backref='empresa', lazy=True)
    eventos = db.relationship('Evento', backref='empresa', lazy=True)
    barracas = db.relationship('Barraca', backref='empresa', lazy=True)
    produtos = db.relationship('Produto', backref='empresa', lazy=True)
    vendas = db.relationship('Venda', backref='empresa', lazy=True)

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    perfil = db.Column(db.String(50), nullable=False, default='vendedor')
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(255))
    reset_token_expira = db.Column(db.DateTime)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.perfil == 'admin'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)

class Barraca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    evento = db.relationship('Evento', backref='barracas')

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    foto = db.Column(db.String(200))
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    barraca_id = db.Column(db.Integer, db.ForeignKey('barraca.id'), nullable=False)
    evento = db.relationship('Evento', backref='produtos')
    barraca = db.relationship('Barraca', backref='produtos')

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    data_venda = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    cancelada = db.Column(db.Boolean, default=False)
    total = db.Column(db.Float, default=0.0)

    evento = db.relationship('Evento', backref='vendas_evento')
    usuario = db.relationship('Usuario', backref='vendas')
    itens = db.relationship('ItemVenda', backref='venda', lazy=True, cascade="all, delete-orphan")
    pagamentos = db.relationship('Pagamento', backref='venda', lazy=True, cascade="all, delete-orphan")

class ItemVenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pago')
    produto = db.relationship('Produto', backref='itens_venda')

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    valor_recebido = db.Column(db.Float)
    troco = db.Column(db.Float)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_sistema = db.Column(db.String(100), default='Sistema Multi-Empresa')
    descricao_sistema = db.Column(db.String(200))
    exibir_rodape = db.Column(db.Boolean, default=True)
    texto_rodape = db.Column(db.String(200))
    cor_menu = db.Column(db.String(7), default='#343a40')
    cor_rodape = db.Column(db.String(7), default='#343a40')
    cor_primaria = db.Column(db.String(7), default='#007bff')
    cor_secundaria = db.Column(db.String(7), default='#6c757d')
    favicon_path = db.Column(db.String(200))
    favicon_version = db.Column(db.String(20))
    ficha_largura_mm = db.Column(db.Float, default=210.0)
    ficha_altura_mm = db.Column(db.Float, default=297.0)
    permitir_registro_empresa = db.Column(db.Boolean, default=True)

# Inicializar o banco de dados
with app.app_context():
    print("INFO: Entrando no app_context para db.create_all()...") # Debug
    try:
        db.create_all()
        print("INFO: db.create_all() executado com sucesso.") # Debug

        # Criar empresa administradora
        empresa_admin = Empresa(
            nome='Administração do Sistema',
            cnpj='00.000.000/0000-00',
            status='aprovado',
            cep='00000-000',
            endereco='Rua Administrativa',
            numero='1',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP'
        )
        db.session.add(empresa_admin)
        db.session.flush()
        
        # Criar usuário administrador
        admin = Usuario(
            nome='Administrador',
            email='admin@sistema.com',
            perfil='admin',
            empresa_id=empresa_admin.id,
            ativo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Criar configuração padrão se não existir
        if Configuracao.query.first() is None:
             print("INFO: Nenhuma configuração encontrada, criando padrão...") # Debug
             db.session.add(Configuracao())
             db.session.commit()
             print("INFO: Configuração padrão criada.") # Debug
    except Exception as e:
         print(f"ERRO durante create_all ou criação de config: {e}") # Debug

if __name__ == '__main__':
    app.run(debug=True) 