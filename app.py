from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
import os
from werkzeug.utils import secure_filename
import json
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, FileField, TextAreaField, FloatField
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
import uuid
from io import BytesIO
from PIL import Image
from sqlalchemy import case
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)

# Configuração do banco de dados PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://sistema:senha_segura@db:5432/sistema')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua_chave_secreta_muito_forte_aqui')

# Configuração do upload de arquivos
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
FOTOS_PRODUTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_produtos')
FOTOS_EVENTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_eventos')
FOTOS_USUARIOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_usuarios')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FOTOS_PRODUTOS_FOLDER'] = FOTOS_PRODUTOS_FOLDER
app.config['FOTOS_EVENTOS_FOLDER'] = FOTOS_EVENTOS_FOLDER
app.config['FOTOS_USUARIOS_FOLDER'] = FOTOS_USUARIOS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Criar diretórios se não existirem
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(FOTOS_PRODUTOS_FOLDER, exist_ok=True)
    os.makedirs(FOTOS_EVENTOS_FOLDER, exist_ok=True)
    os.makedirs(FOTOS_USUARIOS_FOLDER, exist_ok=True)
except Exception as e:
    app.logger.error(f'Erro ao criar diretórios: {str(e)}')

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
    'cor_cabecalho': '#0d6efd',
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    vendas = db.relationship('Venda', backref='empresa_rel', lazy=True)

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
    foto = db.Column(db.String(200))  # Caminho para a foto do usuário

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
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='ativo')

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
    estoque_minimo = db.Column(db.Integer, nullable=False, default=5)
    foto = db.Column(db.String(200))
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    barraca_id = db.Column(db.Integer, db.ForeignKey('barraca.id'), nullable=False)
    evento = db.relationship('Evento', backref='produtos')
    barraca = db.relationship('Barraca', backref='produtos')
    
    @property
    def estoque_baixo(self):
        return self.quantidade <= self.estoque_minimo

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    data_venda = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='concluido')
    total = db.Column(db.Float, nullable=False, default=0.0)
    cancelada = db.Column(db.Boolean, default=False)
    
    # Relacionamentos
    empresa = db.relationship('Empresa', backref='vendas_rel', lazy=True)
    usuario = db.relationship('Usuario', backref='vendas', lazy=True)
    evento = db.relationship('Evento', backref='vendas', lazy=True)
    itens_venda = db.relationship('ItemVenda', backref='venda', lazy=True, cascade="all, delete-orphan")
    pagamentos = db.relationship('Pagamento', backref='venda', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Venda {self.id}>'

class ItemVenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='ativo')  # ativo, cancelado
    produto = db.relationship('Produto', backref='itens_venda')
    
    def __repr__(self):
        return f'<ItemVenda {self.id}>'

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    valor_recebido = db.Column(db.Float)
    troco = db.Column(db.Float)
    
    def __repr__(self):
        return f'<Pagamento {self.id}>'

class BarracaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    descricao = TextAreaField('Descrição')
    evento_id = SelectField('Evento', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')], default='ativo')
    submit = SubmitField('Salvar')

@app.route('/')
def index():
    try:
        if current_user.is_authenticated:
            eventos = Evento.query.filter_by(empresa_id=current_user.empresa_id).order_by(Evento.data_inicio.desc()).all()
            
            # Inicializar carrinho se não existir
            if 'carrinho' not in session:
                session['carrinho'] = {}
            
            # Preparar carrinho com detalhes dos produtos
            carrinho_detalhado = {}
            total_carrinho = 0
            
            # Obter detalhes dos produtos no carrinho
            for prod_id, qtd in session['carrinho'].items():
                prod = Produto.query.get(int(prod_id))
                if prod:
                    carrinho_detalhado[prod_id] = {
                        'nome': prod.nome,
                        'preco': prod.preco,
                        'foto': prod.foto,
                        'quantidade': qtd
                    }
                    total_carrinho += prod.preco * qtd
            
            # Obter evento ativo e seus produtos
            evento_ativo = None
            produtos = []
            if 'evento_ativo_id' in session:
                evento_ativo = Evento.query.get(session['evento_ativo_id'])
                if evento_ativo:
                    produtos = Produto.query.filter_by(evento_id=evento_ativo.id).all()
            
            return render_template('index.html', 
                                eventos=eventos, 
                                carrinho=carrinho_detalhado,
                                total_carrinho=total_carrinho,
                                evento_ativo=evento_ativo,
                                produtos=produtos)
        else:
            return redirect(url_for('login'))
    except Exception as e:
        app.logger.error(f'Erro na página inicial: {str(e)}')
        flash('Ocorreu um erro ao carregar a página inicial', 'error')
        return redirect(url_for('login'))

@app.route('/selecionar_evento', methods=['POST'])
@login_required
def selecionar_evento():
    try:
        evento_id = request.form.get('evento_id')
        if evento_id:
            evento = Evento.query.get_or_404(evento_id)
            if evento.empresa_id != current_user.empresa_id:
                flash('Acesso negado', 'error')
                return redirect(url_for('index'))
            
            session['evento_ativo_id'] = evento.id
            flash(f'Evento "{evento.nome}" selecionado com sucesso!', 'success')
        else:
            if 'evento_ativo_id' in session:
                del session['evento_ativo_id']
            flash('Nenhum evento selecionado', 'info')
        
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        app.logger.error(f'Erro ao selecionar evento: {str(e)}')
        flash('Erro ao selecionar evento', 'error')
        return redirect(url_for('index'))

# Modificar o contexto do template base
@app.context_processor
def inject_eventos():
    if current_user.is_authenticated:
        eventos = Evento.query.filter_by(empresa_id=current_user.empresa_id).order_by(Evento.data_inicio.desc()).all()
        evento_ativo = None
        if 'evento_ativo_id' in session:
            evento_ativo = Evento.query.get(session['evento_ativo_id'])
        return dict(eventos=eventos, evento_ativo=evento_ativo)
    return dict(eventos=[], evento_ativo=None)

@app.route('/evento/novo', methods=['GET', 'POST'])
@login_required
def novo_evento():
    try:
        if request.method == 'POST':
            # Verificar se todos os campos necessários estão presentes
            if not all(k in request.form for k in ['nome', 'data', 'hora_inicio', 'hora_fim']):
                flash('Todos os campos são obrigatórios', 'error')
                return redirect(url_for('novo_evento'))
            
            nome = request.form['nome']
            data = request.form['data']
            hora_inicio = request.form['hora_inicio']
            hora_fim = request.form['hora_fim']
            
            try:
                # Combinar data com hora de início e fim
                data_inicio = datetime.strptime(f"{data} {hora_inicio}", '%Y-%m-%d %H:%M')
                data_fim = datetime.strptime(f"{data} {hora_fim}", '%Y-%m-%d %H:%M')
                
                # Verificar se a data de fim é posterior à data de início
                if data_fim <= data_inicio:
                    flash('A hora de término deve ser posterior à hora de início', 'error')
                    return redirect(url_for('novo_evento'))
                
                evento = Evento(
                    empresa_id=current_user.empresa_id,
                    nome=nome,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                
                db.session.add(evento)
                db.session.commit()
                
                flash('Evento criado com sucesso!', 'success')
                return redirect(url_for('listar_eventos'))
                
            except ValueError as e:
                flash('Formato de data ou hora inválido', 'error')
                return redirect(url_for('novo_evento'))
            
        # Obter data e hora atual para preencher o formulário
        data_atual = datetime.now().strftime('%Y-%m-%d')
        hora_atual = datetime.now().strftime('%H:%M')
        
        return render_template('novo_evento.html', data_atual=data_atual, hora_atual=hora_atual)
    except Exception as e:
        app.logger.error(f'Erro ao criar evento: {str(e)}')
        flash('Erro ao criar evento', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/eventos/<int:evento_id>')
@login_required
def visualizar_evento(evento_id):
    try:
        evento = Evento.query.get_or_404(evento_id)
        if evento.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
        barracas = Barraca.query.filter_by(evento_id=evento_id).all()
        return render_template('visualizar_evento.html', evento=evento, barracas=barracas)
    except Exception as e:
        app.logger.error(f'Erro ao visualizar evento: {str(e)}')
        flash('Erro ao visualizar evento', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/produtos')
@login_required
def listar_produtos():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' in session:
            evento_id = session['evento_ativo_id']
            produtos = Produto.query.filter_by(
                empresa_id=current_user.empresa_id,
                evento_id=evento_id
            ).all()
        else:
            produtos = []
            flash('Selecione um evento para visualizar os produtos.', 'info')
        
        return render_template('listar_produtos.html', produtos=produtos)
    except Exception as e:
        app.logger.error(f'Erro ao listar produtos: {str(e)}')
        flash('Erro ao listar produtos', 'error')
        return redirect(url_for('index'))

@app.route('/produto/novo', methods=['GET', 'POST'])
@login_required
def novo_produto():
    try:
        if request.method == 'POST':
            nome = request.form['nome']
            descricao = request.form['descricao']
            preco = float(request.form['preco'])
            quantidade = int(request.form['quantidade'])
            evento_id = int(request.form['evento_id'])
            
            evento = Evento.query.get_or_404(evento_id)
            if evento.empresa_id != current_user.empresa_id:
                flash('Acesso negado. Você não pode criar produtos em eventos de outras empresas.', 'error')
                return redirect(url_for('listar_produtos'))
            
            novo_produto = Produto(
                nome=nome,
                descricao=descricao,
                preco=preco,
                quantidade=quantidade,
                evento_id=evento_id,
                empresa_id=current_user.empresa_id
            )
            
            if 'foto' in request.files:
                foto = request.files['foto']
                if foto and allowed_file(foto.filename):
                    filename = secure_filename(foto.filename)
                    foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    novo_produto.foto = filename
            
            db.session.add(novo_produto)
            db.session.commit()
            flash('Produto criado com sucesso', 'success')
            return redirect(url_for('listar_produtos'))
        
        eventos = Evento.query.filter_by(empresa_id=current_user.empresa_id).all()
        return render_template('novo_produto.html', eventos=eventos)
    except Exception as e:
        app.logger.error(f'Erro ao criar produto: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao criar o produto', 'error')
        return redirect(url_for('listar_produtos'))

@app.route('/ficha_html/<int:venda_id>')
@login_required
def ficha_html(venda_id):
    try:
        venda = Venda.query.get_or_404(venda_id)
        if venda.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_vendas'))
        
        # Obter todos os itens da venda
        itens_venda = venda.itens_venda
        if not itens_venda:
            flash('Venda sem itens', 'error')
            return redirect(url_for('listar_vendas'))
        
        # Obter a forma de pagamento
        pagamento = venda.pagamentos[0] if venda.pagamentos else None
        forma_pagamento = pagamento.forma_pagamento if pagamento else 'Não informado'
        
        # Lista para armazenar as fichas
        fichas = []
        
        for item_venda in itens_venda:
            # Gerar QR Code para cada item
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Dados para o QR Code
            qr_data = {
                'venda_id': venda.id,
                'produto': item_venda.produto.nome,
                'evento': venda.evento.nome,
                'data': venda.data_venda.strftime('%d/%m/%Y %H:%M:%S'),
                'forma_pagamento': forma_pagamento
            }
            
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            # Criar imagem do QR Code
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converter para base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Adicionar ficha para cada item
            fichas.append({
                'item_venda': item_venda,
                'qr_code_base64': qr_code_base64
            })
        
        return render_template('ficha_html.html', 
                             venda=venda, 
                             fichas=fichas,
                             forma_pagamento=forma_pagamento)
    except Exception as e:
        app.logger.error(f'Erro ao gerar ficha: {str(e)}')
        flash('Erro ao gerar ficha', 'error')
        return redirect(url_for('listar_vendas'))

def imprimir_ficha(venda):
    try:
        return venda.id
    except Exception as e:
        print(f"Erro ao gerar ficha: {str(e)}")
        return None

@app.route('/vendas')
@login_required
def listar_vendas():
    try:
        vendas = Venda.query.join(Produto).filter(Produto.empresa_id == current_user.empresa_id).all()
        return render_template('listar_vendas.html', vendas=vendas)
    except Exception as e:
        app.logger.error(f'Erro ao listar vendas: {str(e)}')
        flash('Ocorreu um erro ao listar as vendas', 'error')
        return redirect(url_for('index'))

@app.route('/relatorios/vendas')
@login_required
def relatorio_vendas():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' not in session:
            flash('Selecione um evento primeiro', 'warning')
            return redirect(url_for('index'))
            
        # Obter parâmetros de filtro
        id_venda = request.args.get('id_venda')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        barraca_id = request.args.get('barraca')
        forma_pagamento = request.args.get('forma_pagamento')
        vendedor_id = request.args.get('vendedor')
        status = request.args.get('status')
        
        # Construir a query base
        query = (Venda.query
                .select_from(Venda)
                .join(Evento, Venda.evento_id == Evento.id)
                .join(ItemVenda, Venda.id == ItemVenda.venda_id)
                .join(Produto, ItemVenda.produto_id == Produto.id)
                .join(Barraca, Produto.barraca_id == Barraca.id)
                .join(Pagamento, Venda.id == Pagamento.venda_id)
                .join(Usuario, Venda.usuario_id == Usuario.id)
                .filter(Venda.empresa_id == current_user.empresa_id)
                .filter(Venda.evento_id == session['evento_ativo_id']))
        
        # Aplicar filtros
        if id_venda:
            query = query.filter(Venda.id == id_venda)
        if data_inicio:
            query = query.filter(Venda.data_venda >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Venda.data_venda <= datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1))
        if barraca_id:
            query = query.filter(Produto.barraca_id == barraca_id)
        if forma_pagamento:
            query = query.filter(Pagamento.forma_pagamento == forma_pagamento)
        if vendedor_id:
            query = query.filter(Venda.usuario_id == vendedor_id)
        if status:
            if status == 'ativa':
                query = query.filter(Venda.cancelada.is_(False))
            elif status == 'cancelada':
                query = query.filter(Venda.cancelada.is_(True))
        
        # Ordenar por data mais recente
        vendas = query.order_by(Venda.data_venda.desc()).all()
        
        # Agrupar os dados por venda
        vendas_agrupadas = {}
        for venda in vendas:
            if venda.id not in vendas_agrupadas:
                vendas_agrupadas[venda.id] = {
                    'id': venda.id,
                    'data_venda': venda.data_venda,
                    'barraca': venda.itens_venda[0].produto.barraca.nome if venda.itens_venda else 'N/A',
                    'forma_pagamento': venda.pagamentos[0].forma_pagamento if venda.pagamentos else 'N/A',
                    'total_venda': venda.total,
                    'usuario': venda.usuario.nome,
                    'cancelada': venda.cancelada,
                    'itens': []
                }
            
            # Adicionar os itens da venda individualmente
            for item in venda.itens_venda:
                # Adicionar um item para cada quantidade atual
                for _ in range(item.quantidade):
                    vendas_agrupadas[venda.id]['itens'].append({
                        'id': item.id,
                        'produto': item.produto.nome,
                        'quantidade': 1,  # Cada item tem quantidade 1
                        'preco_unitario': item.preco_unitario,
                        'total': item.preco_unitario,
                        'status': 'Ativo'
                    })
        
        # Converter o dicionário em lista ordenada por data
        vendas_lista = sorted(vendas_agrupadas.values(), key=lambda x: x['data_venda'], reverse=True)
        
        # Obter listas para os filtros
        barracas = Barraca.query.filter_by(evento_id=session['evento_ativo_id']).all()
        usuarios = Usuario.query.filter_by(empresa_id=current_user.empresa_id).all()
        
        return render_template('relatorio_vendas.html', 
                             vendas=vendas_lista,
                             barracas=barracas,
                             usuarios=usuarios)
        
    except Exception as e:
        app.logger.error(f'Erro ao gerar relatório de vendas: {str(e)}')
        flash('Erro ao gerar relatório de vendas', 'error')
        return redirect(url_for('index'))

@app.route('/relatorio_produtos')
@login_required
def relatorio_produtos():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' not in session:
            flash('Selecione um evento para visualizar o relatório de produtos.', 'info')
            return redirect(url_for('index'))
            
        evento_id = session['evento_ativo_id']
        barraca_id = request.args.get('barraca_id')
        
        # Buscar produtos com quantidade vendida e estornada
        query = db.session.query(
            Produto,
            db.func.coalesce(db.func.sum(case((Venda.cancelada.is_(True), ItemVenda.quantidade), else_=0)).label('quantidade_estornada'), 0),
            db.func.coalesce(db.func.sum(case((Venda.cancelada.is_(False), ItemVenda.quantidade), else_=0)).label('quantidade_vendida'), 0)
        )\
        .select_from(Produto)\
        .join(Barraca, Produto.barraca_id == Barraca.id)\
        .join(Evento, Barraca.evento_id == Evento.id)\
        .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)\
        .outerjoin(Venda, ItemVenda.venda_id == Venda.id)\
        .filter(
            Evento.id == evento_id,
            Evento.empresa_id == current_user.empresa_id
        )
        
        # Aplicar filtro de barraca se especificado
        if barraca_id:
            query = query.filter(Produto.barraca_id == barraca_id)
        
        produtos = query.group_by(Produto.id)\
            .order_by(Produto.nome)\
            .all()
        
        # Buscar todas as barracas do evento para o filtro
        barracas = Barraca.query.filter_by(evento_id=evento_id).all()
        
        # Obter o evento ativo
        evento_ativo = Evento.query.get(evento_id)
        
        # Preparar dados para o template
        produtos_com_quantidade = []
        for produto, quantidade_estornada, quantidade_vendida in produtos:
            produtos_com_quantidade.append({
                'produto': produto,
                'quantidade_vendida': quantidade_vendida,
                'quantidade_estornada': quantidade_estornada
            })
            
        return render_template('relatorio_produtos.html', 
                             produtos=produtos_com_quantidade,
                             barracas=barracas,
                             barraca_selecionada=barraca_id,
                             evento_ativo=evento_ativo)
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório de produtos: {str(e)}")
        flash('Erro ao gerar relatório de produtos. Por favor, tente novamente.', 'error')
        return redirect(url_for('index'))

@app.route('/relatorio_produtos/pdf')
@login_required
def relatorio_produtos_pdf():
    try:
        if 'evento_ativo_id' not in session:
            flash('Selecione um evento para gerar o relatório em PDF.', 'info')
            return redirect(url_for('index'))
            
        evento_id = session['evento_ativo_id']
        barraca_id = request.args.get('barraca_id')
        
        # Buscar produtos com quantidade vendida
        query = db.session.query(
            Produto,
            db.func.coalesce(db.func.sum(ItemVenda.quantidade), 0).label('quantidade_vendida')
        )\
        .select_from(Produto)\
        .join(Barraca, Produto.barraca_id == Barraca.id)\
        .join(Evento, Barraca.evento_id == Evento.id)\
        .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)\
        .filter(
            Evento.id == evento_id,
            Evento.empresa_id == current_user.empresa_id
        )
        
        if barraca_id:
            query = query.filter(Produto.barraca_id == barraca_id)
        
        produtos = query.group_by(Produto.id)\
            .order_by(Produto.nome)\
            .all()
        
        # Preparar dados para o PDF
        produtos_com_quantidade = []
        for produto, quantidade_vendida in produtos:
            produtos_com_quantidade.append({
                'produto': produto,
                'quantidade_vendida': quantidade_vendida,
                'quantidade_restante': produto.quantidade - quantidade_vendida
            })
        
        # Gerar PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=landscape(letter))
        
        # Configurar margens (1cm = 28 pontos)
        margem = 28
        largura_pagina = landscape(letter)[0]
        altura_pagina = landscape(letter)[1]
        
        # Configurar o PDF
        p.setTitle("Relatório de Produtos")
        p.setFont("Helvetica-Bold", 16)
        p.drawString(margem, altura_pagina - margem - 20, "Relatório de Produtos")
        
        # Informações do evento
        evento = Evento.query.get(evento_id)
        p.setFont("Helvetica", 12)
        p.drawString(margem, altura_pagina - margem - 50, f"Evento: {evento.nome}")
        if barraca_id:
            barraca = Barraca.query.get(barraca_id)
            p.drawString(margem, altura_pagina - margem - 70, f"Barraca: {barraca.nome}")
        
        # Cabeçalho da tabela
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margem, altura_pagina - margem - 100, "Produto")
        p.drawString(margem + 150, altura_pagina - margem - 100, "Barraca")
        p.drawString(margem + 300, altura_pagina - margem - 100, "Unitário")
        p.drawString(margem + 380, altura_pagina - margem - 100, "Vendido")
        p.drawString(margem + 460, altura_pagina - margem - 100, "Estoque")
        p.drawString(margem + 540, altura_pagina - margem - 100, "Vendidos")
        p.drawString(margem + 620, altura_pagina - margem - 100, "Disponível")
        
        # Dados da tabela
        p.setFont("Helvetica", 10)
        y = altura_pagina - margem - 120
        for item in produtos_com_quantidade:
            if y < margem + 50:  # Nova página se necessário
                p.showPage()
                y = altura_pagina - margem - 20
                # Redesenhar cabeçalho
                p.setFont("Helvetica-Bold", 10)
                p.drawString(margem, y, "Produto")
                p.drawString(margem + 150, y, "Barraca")
                p.drawString(margem + 300, y, "Unitário")
                p.drawString(margem + 380, y, "Vendido")
                p.drawString(margem + 460, y, "Estoque")
                p.drawString(margem + 540, y, "Vendidos")
                p.drawString(margem + 620, y, "Disponível")
                y = altura_pagina - margem - 40
                p.setFont("Helvetica", 10)
            
            p.drawString(margem, y, item['produto'].nome)
            p.drawString(margem + 150, y, item['produto'].barraca.nome)
            p.drawString(margem + 300, y, f"R$ {item['produto'].preco:.2f}".replace('.', ','))
            p.drawString(margem + 380, y, f"R$ {(item['produto'].preco * item['quantidade_vendida']):.2f}".replace('.', ','))
            p.drawString(margem + 460, y, str(item['produto'].quantidade))
            p.drawString(margem + 540, y, str(item['quantidade_vendida']))
            p.drawString(margem + 620, y, str(item['quantidade_restante']))
            y -= 20
        
        # Adicionar linha de totalizadores
        y -= 20  # Espaço extra antes dos totais
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margem, y, "Totais:")
        
        # Calcular totais
        total_estoque = sum(item['produto'].quantidade for item in produtos_com_quantidade)
        total_vendidos = sum(item['quantidade_vendida'] for item in produtos_com_quantidade)
        total_disponivel = sum(item['quantidade_restante'] for item in produtos_com_quantidade)
        total_vendido = sum(item['produto'].preco * item['quantidade_vendida'] for item in produtos_com_quantidade)
        
        p.drawString(margem + 380, y, f"R$ {total_vendido:.2f}".replace('.', ','))
        p.drawString(margem + 460, y, str(total_estoque))
        p.drawString(margem + 540, y, str(total_vendidos))
        p.drawString(margem + 620, y, str(total_disponivel))
        
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"relatorio_produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar PDF do relatório de produtos: {str(e)}")
        flash('Erro ao gerar PDF do relatório. Por favor, tente novamente.', 'error')
        return redirect(url_for('relatorio_produtos'))

@app.route('/venda/nova', methods=['GET', 'POST'])
@login_required
def nova_venda():
    try:
        if request.method == 'POST':
            produto_id = int(request.form['produto_id'])
            quantidade = int(request.form['quantidade'])
            forma_pagamento = request.form['forma_pagamento']
            
            produto = Produto.query.get_or_404(produto_id)
            if produto.empresa_id != current_user.empresa_id:
                flash('Acesso negado. Você não pode realizar vendas de produtos de outras empresas.', 'error')
                return redirect(url_for('listar_vendas'))
            
            if produto.quantidade < quantidade:
                flash('Quantidade insuficiente em estoque', 'error')
                return redirect(url_for('nova_venda'))
            
            nova_venda = Venda(
                produto_id=produto_id,
                quantidade=quantidade,
                valor_total=produto.preco * quantidade,
                forma_pagamento=forma_pagamento,
                usuario_id=current_user.id
            )
            
            produto.quantidade -= quantidade
            
            db.session.add(nova_venda)
            db.session.commit()
            flash('Venda realizada com sucesso', 'success')
            return redirect(url_for('listar_vendas'))
        
        produtos = Produto.query.filter_by(empresa_id=current_user.empresa_id).all()
        return render_template('nova_venda.html', produtos=produtos)
    except Exception as e:
        app.logger.error(f'Erro ao criar venda: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao realizar a venda', 'error')
        return redirect(url_for('listar_vendas'))

@app.route('/adicionar_ao_carrinho/<int:produto_id>', methods=['POST'])
@login_required
def adicionar_ao_carrinho(produto_id):
    try:
        produto = Produto.query.get_or_404(produto_id)
        if produto.empresa_id != current_user.empresa_id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
            
        data = request.get_json()
        quantidade = int(data.get('quantidade', 1))
        
        # Verificar se a quantidade excede o estoque
        if quantidade > produto.quantidade:
            return jsonify({'success': False, 'message': f'Quantidade solicitada ({quantidade}) maior que o estoque disponível ({produto.quantidade})'})
        
        # Inicializar carrinho se não existir
        if 'carrinho' not in session:
            session['carrinho'] = {}
            
        # Verificar quantidade total no carrinho
        quantidade_total = quantidade
        if str(produto_id) in session['carrinho']:
            quantidade_total += session['carrinho'][str(produto_id)]
            
        if quantidade_total > produto.quantidade:
            return jsonify({'success': False, 'message': f'Quantidade total ({quantidade_total}) excederia o estoque disponível ({produto.quantidade})'})
            
        # Adicionar ou atualizar a quantidade no carrinho
        carrinho = session.get('carrinho', {}).copy()
        if str(produto_id) in carrinho:
            carrinho[str(produto_id)] += quantidade
        else:
            carrinho[str(produto_id)] = quantidade
            
        # Atualizar a sessão com o novo carrinho
        session['carrinho'] = carrinho
        
        # Preparar carrinho detalhado para retorno
        carrinho_detalhado = {}
        total_carrinho = 0
        
        for prod_id, qtd in carrinho.items():
            prod = Produto.query.get(int(prod_id))
            if prod:
                carrinho_detalhado[prod_id] = {
                    'nome': prod.nome,
                    'preco': prod.preco,
                    'foto': prod.foto,
                    'quantidade': qtd
                }
                total_carrinho += prod.preco * qtd
        
        # Forçar a atualização da sessão
        session.modified = True
            
        return jsonify({
            'success': True, 
            'message': 'Produto adicionado ao carrinho!',
            'carrinho': carrinho_detalhado,
            'total_carrinho': total_carrinho
        })
    except Exception as e:
        app.logger.error(f'Erro ao adicionar ao carrinho: {str(e)}')
        return jsonify({'success': False, 'message': 'Erro ao adicionar ao carrinho'})

@app.route('/remover_do_carrinho/<int:produto_id>', methods=['POST'])
@login_required
def remover_do_carrinho(produto_id):
    try:
        # Verificar se o carrinho existe na sessão
        if 'carrinho' not in session:
            return jsonify({'success': False, 'message': 'Carrinho não encontrado'})
            
        # Copiar o carrinho atual
        carrinho = session.get('carrinho', {}).copy()
        
        # Verificar se o produto está no carrinho
        if str(produto_id) not in carrinho:
            return jsonify({'success': False, 'message': 'Produto não encontrado no carrinho'})
            
        # Remover o produto do carrinho
        del carrinho[str(produto_id)]
        
        # Atualizar a sessão com o novo carrinho
        session['carrinho'] = carrinho
        
        # Calcular o novo total
        total_carrinho = 0
        carrinho_detalhado = {}
        
        for prod_id, qtd in carrinho.items():
            prod = Produto.query.get(int(prod_id))
            if prod:
                carrinho_detalhado[prod_id] = {
                    'nome': prod.nome,
                    'preco': prod.preco,
                    'foto': prod.foto,
                    'quantidade': qtd
                }
                total_carrinho += prod.preco * qtd
        
        # Forçar a atualização da sessão
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Produto removido do carrinho!',
            'carrinho': carrinho_detalhado,
            'total_carrinho': total_carrinho
        })
    except Exception as e:
        app.logger.error(f'Erro ao remover do carrinho: {str(e)}')
        return jsonify({'success': False, 'message': 'Erro ao remover do carrinho'})

@app.route('/atualizar_carrinho/<int:produto_id>', methods=['POST'])
@login_required
def atualizar_carrinho(produto_id):
    try:
        quantidade = int(request.form.get('quantidade', 1))
        if quantidade <= 0:
            return redirect(url_for('remover_do_carrinho', produto_id=produto_id))
            
        if 'carrinho' in session and str(produto_id) in session['carrinho']:
            session['carrinho'][str(produto_id)] = quantidade
            flash('Carrinho atualizado!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f'Erro ao atualizar carrinho: {str(e)}')
        flash('Erro ao atualizar carrinho', 'error')
        return redirect(url_for('index'))

@app.route('/limpar_carrinho', methods=['POST'])
@login_required
def limpar_carrinho():
    try:
        session['carrinho'] = {}
        flash('Carrinho limpo!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f'Erro ao limpar carrinho: {str(e)}')
        flash('Erro ao limpar carrinho', 'error')
        return redirect(url_for('index'))

@app.route('/produtos/<int:produto_id>')
@login_required
def visualizar_produto(produto_id):
    try:
        produto = Produto.query.get_or_404(produto_id)
        if produto.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_produtos'))
        return render_template('visualizar_produto.html', produto=produto)
    except Exception as e:
        app.logger.error(f'Erro ao visualizar produto: {str(e)}')
        flash('Erro ao visualizar produto', 'error')
        return redirect(url_for('listar_produtos'))

@app.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    try:
        produto = Produto.query.get_or_404(produto_id)
        if produto.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_produtos'))
            
        if request.method == 'POST':
            produto.nome = request.form['nome']
            # Trata o preço que vem formatado como moeda
            preco_str = request.form['preco'].replace('.', '').replace(',', '.')
            produto.preco = float(preco_str)
            produto.quantidade = int(request.form['quantidade'])
            
            # Verifica se deve remover a foto atual
            if request.form.get('remover_foto') == '1':
                if produto.foto:
                    # Remove o arquivo físico
                    foto_path = os.path.join(app.config['UPLOAD_FOLDER'], produto.foto)
                    if os.path.exists(foto_path):
                        os.remove(foto_path)
                    produto.foto = None
            
            # Verifica se foi enviada uma nova foto
            if 'foto' in request.files:
                foto = request.files['foto']
                if foto and allowed_file(foto.filename):
                    # Remove a foto antiga se existir
                    if produto.foto:
                        foto_antiga = os.path.join(app.config['UPLOAD_FOLDER'], produto.foto)
                        if os.path.exists(foto_antiga):
                            os.remove(foto_antiga)
                    
                    # Salva a nova foto com UUID
                    filename = secure_filename(foto.filename)
                    foto = f"{uuid.uuid4().hex}_{filename}"
                    foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto))
                    produto.foto = foto
            
            db.session.commit()
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('visualizar_produto', produto_id=produto_id))
            
        return render_template('editar_produto.html', produto=produto)
    except Exception as e:
        app.logger.error(f'Erro ao editar produto: {str(e)}')
        flash('Erro ao editar produto', 'error')
        return redirect(url_for('visualizar_produto', produto_id=produto_id))

@app.route('/produtos/<int:produto_id>/excluir', methods=['POST'])
@login_required
def excluir_produto(produto_id):
    try:
        produto = Produto.query.get_or_404(produto_id)
        if produto.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_produtos'))
            
        db.session.delete(produto)
        db.session.commit()
        flash('Produto excluído com sucesso!', 'success')
        return redirect(url_for('listar_produtos'))
    except Exception as e:
        app.logger.error(f'Erro ao excluir produto: {str(e)}')
        flash('Erro ao excluir produto', 'error')
        return redirect(url_for('listar_produtos'))

@app.route('/eventos')
@login_required
def listar_eventos():
    try:
        eventos = Evento.query.filter_by(empresa_id=current_user.empresa_id).order_by(Evento.data_inicio.desc()).all()
        return render_template('listar_eventos.html', eventos=eventos)
    except Exception as e:
        app.logger.error(f'Erro ao listar eventos: {str(e)}')
        flash('Ocorreu um erro ao listar os eventos', 'error')
        return redirect(url_for('index'))

@app.route('/eventos/<int:evento_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_evento(evento_id):
    try:
        evento = Evento.query.get_or_404(evento_id)
        if evento.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        if request.method == 'POST':
            nome = request.form['nome']
            data = request.form['data']
            hora_inicio = request.form['hora_inicio']
            hora_fim = request.form['hora_fim']
            
            try:
                # Combinar data com hora de início e fim
                data_inicio = datetime.strptime(f"{data} {hora_inicio}", '%Y-%m-%d %H:%M')
                data_fim = datetime.strptime(f"{data} {hora_fim}", '%Y-%m-%d %H:%M')
                
                # Verificar se a data de fim é posterior à data de início
                if data_fim <= data_inicio:
                    flash('A hora de término deve ser posterior à hora de início', 'error')
                    return redirect(url_for('editar_evento', evento_id=evento_id))
                
                evento.nome = nome
                evento.data_inicio = data_inicio
                evento.data_fim = data_fim
                
                db.session.commit()
                flash('Evento atualizado com sucesso!', 'success')
                return redirect(url_for('listar_eventos'))
                
            except ValueError as e:
                flash('Formato de data ou hora inválido', 'error')
                return redirect(url_for('editar_evento', evento_id=evento_id))
            
        return render_template('editar_evento.html', evento=evento)
    except Exception as e:
        app.logger.error(f'Erro ao editar evento: {str(e)}')
        flash('Erro ao editar evento', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/eventos/<int:evento_id>/excluir', methods=['POST'])
@login_required
def excluir_evento(evento_id):
    try:
        # Verificar se o usuário é administrador
        if current_user.perfil != 'admin':
            flash('Acesso negado. Apenas administradores podem excluir eventos.', 'error')
            return redirect(url_for('listar_eventos'))
            
        # Verificar senha do usuário
        senha = request.form.get('senha')
        if not senha:
            flash('Por favor, informe sua senha para confirmar a exclusão.', 'warning')
            return redirect(url_for('listar_eventos'))
            
        if not current_user.check_password(senha):
            flash('Senha incorreta. Por favor, tente novamente.', 'error')
            return redirect(url_for('listar_eventos'))
            
        evento = Evento.query.get_or_404(evento_id)
        if evento.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        # Excluir todas as vendas e seus itens/pagamentos
        vendas = Venda.query.filter_by(evento_id=evento_id).all()
        for venda in vendas:
            # Excluir itens da venda
            ItemVenda.query.filter_by(venda_id=venda.id).delete()
            # Excluir pagamentos da venda
            Pagamento.query.filter_by(venda_id=venda.id).delete()
            # Excluir a venda
            db.session.delete(venda)
        
        # Excluir todos os produtos
        Produto.query.filter_by(evento_id=evento_id).delete()
        
        # Excluir todas as barracas
        Barraca.query.filter_by(evento_id=evento_id).delete()
        
        # Excluir o evento
        db.session.delete(evento)
        db.session.commit()
        
        flash('Evento e todas as suas dependências foram excluídos com sucesso!', 'success')
        return redirect(url_for('listar_eventos'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao excluir evento: {str(e)}')
        flash('Erro ao excluir evento.', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/barracas')
@login_required
def listar_todas_barracas():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' in session:
            evento_id = session['evento_ativo_id']
            barracas = Barraca.query.filter_by(
                evento_id=evento_id
            ).join(Evento).filter(
                Evento.empresa_id == current_user.empresa_id
            ).all()
        else:
            barracas = []
            flash('Selecione um evento para visualizar as barracas.', 'info')
        
        return render_template('listar_barracas.html', barracas=barracas)
    except Exception as e:
        app.logger.error(f"Erro ao listar barracas: {str(e)}")
        flash('Erro ao listar barracas. Por favor, tente novamente.', 'error')
        return redirect(url_for('index'))

@app.route('/barraca/novo', methods=['GET', 'POST'])
@login_required
def nova_barraca():
    try:
        evento_id = request.args.get('evento_id')
        if not evento_id:
            flash('Evento não especificado', 'error')
            return redirect(url_for('listar_eventos'))
            
        evento = Evento.query.get_or_404(evento_id)
        if evento.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        if request.method == 'POST':
            nome = request.form['nome']
            descricao = request.form['descricao']
            
            barraca = Barraca(
                nome=nome,
                descricao=descricao,
                evento_id=evento_id,
                empresa_id=current_user.empresa_id
            )
            
            db.session.add(barraca)
            db.session.commit()
            flash('Barraca criada com sucesso!', 'success')
            return redirect(url_for('visualizar_evento', evento_id=evento_id))
            
        return render_template('nova_barraca.html', evento=evento)
    except Exception as e:
        app.logger.error(f"Erro ao criar barraca: {str(e)}")
        flash('Erro ao criar barraca. Por favor, tente novamente.', 'error')
        return redirect(url_for('visualizar_evento', evento_id=evento_id))

@app.route('/barracas/<int:barraca_id>/produtos/novo', methods=['GET', 'POST'])
@login_required
def novo_produto_barraca(barraca_id):
    try:
        barraca = Barraca.query.get_or_404(barraca_id)
        if barraca.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        if request.method == 'POST':
            nome = request.form['nome']
            preco = float(request.form['preco'])
            quantidade = int(request.form['quantidade_estoque'])
            estoque_minimo = int(request.form.get('estoque_minimo', 5))
            
            # Verificar se foi enviada uma foto
            foto = None
            if 'foto' in request.files and request.files['foto'].filename:
                arquivo = request.files['foto']
                if arquivo and allowed_file(arquivo.filename):
                    filename = secure_filename(arquivo.filename)
                    foto = f"{uuid.uuid4().hex}_{filename}"
                    arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], foto))
            
            produto = Produto(
                nome=nome,
                preco=preco,
                quantidade=quantidade,
                estoque_minimo=estoque_minimo,
                barraca_id=barraca_id,
                evento_id=barraca.evento_id,
                empresa_id=current_user.empresa_id,
                foto=foto
            )
            
            db.session.add(produto)
            db.session.commit()
            flash('Produto criado com sucesso!', 'success')
            return redirect(url_for('visualizar_evento', evento_id=barraca.evento_id))
            
        return render_template('novo_produto.html', barraca=barraca)
    except Exception as e:
        app.logger.error(f"Erro ao criar produto: {str(e)}")
        flash('Erro ao criar produto. Por favor, tente novamente.', 'error')
        return redirect(url_for('visualizar_evento', evento_id=barraca.evento_id))

@app.route('/barracas/<int:barraca_id>/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto_barraca(barraca_id, produto_id):
    barraca = Barraca.query.get_or_404(barraca_id)
    produto = Produto.query.get_or_404(produto_id)
    
    if barraca.empresa_id != current_user.empresa_id:
        flash('Você não tem permissão para editar este produto.', 'error')
        return redirect(url_for('visualizar_evento', evento_id=barraca.evento_id))
    
    if request.method == 'POST':
        produto.nome = request.form.get('nome')
        produto.preco = float(request.form.get('preco'))
        produto.quantidade = int(request.form.get('quantidade'))
        produto.estoque_minimo = int(request.form.get('estoque_minimo', 5))
        
        # Verifica se deve remover a foto atual
        if request.form.get('remover_foto') == '1':
            if produto.foto:
                # Remove o arquivo físico
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], produto.foto)
                if os.path.exists(foto_path):
                    os.remove(foto_path)
                produto.foto = None
        
        # Verifica se foi enviada uma nova foto
        if 'foto' in request.files:
            arquivo = request.files['foto']
            if arquivo.filename != '':
                if produto.foto:
                    # Remove a foto antiga
                    foto_antiga = os.path.join(app.config['UPLOAD_FOLDER'], produto.foto)
                    if os.path.exists(foto_antiga):
                        os.remove(foto_antiga)
                
                # Salva a nova foto com UUID
                filename = secure_filename(arquivo.filename)
                novo_nome = f"{uuid.uuid4().hex}_{filename}"
                arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], novo_nome))
                produto.foto = novo_nome
        
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('visualizar_evento', evento_id=barraca.evento_id))
    
    return render_template('editar_produto.html', barraca=barraca, produto=produto)

@app.route('/usuarios')
@login_required
def listar_usuarios():
    try:
        if current_user.perfil not in ['admin', 'gerente']:
            flash('Acesso negado. Apenas administradores e gerentes podem acessar esta página.', 'error')
            return redirect(url_for('index'))
        
        usuarios = Usuario.query.filter_by(empresa_id=current_user.empresa_id).all()
        return render_template('listar_usuarios.html', usuarios=usuarios)
    except Exception as e:
        app.logger.error(f'Erro ao listar usuários: {str(e)}')
        flash('Ocorreu um erro ao listar os usuários', 'error')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form['email']
            senha = request.form['senha']
            usuario = Usuario.query.filter_by(email=email).first()
            
            if usuario and usuario.check_password(senha):
                login_user(usuario)
                return redirect(url_for('index'))
            else:
                flash('Email ou senha inválidos', 'error')
        return render_template('login.html')
    except Exception as e:
        app.logger.error(f'Erro no login: {str(e)}')
        flash('Ocorreu um erro durante o login', 'error')
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f'Erro no logout: {str(e)}')
        flash('Ocorreu um erro ao fazer logout', 'error')
        return redirect(url_for('index'))

@app.route('/criar_admin', methods=['GET', 'POST'])
def criar_admin():
    # Verificar se já existe algum usuário no sistema
    if Usuario.query.first():
        flash('Já existe um usuário administrador no sistema.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        # Criar empresa padrão
        empresa = Empresa(
            nome='Empresa Padrão',
            cnpj='00000000000000',
            cep='00000000',
            endereco='Endereço Padrão',
            numero='0',
            complemento='',
            bairro='Bairro Padrão',
            cidade='Cidade Padrão',
            estado='SP',
            status='aprovado'
        )
        db.session.add(empresa)
        db.session.commit()
        
        # Criar usuário administrador
        admin = Usuario(
            nome=nome,
            email=email,
            perfil='admin',
            empresa_id=empresa.id
        )
        admin.set_password(senha)
        db.session.add(admin)
        db.session.commit()
        
        flash('Administrador criado com sucesso!', 'success')
        return redirect(url_for('login'))
    
    return render_template('criar_admin.html')

@app.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario_empresa():
    try:
        if current_user.perfil not in ['admin', 'gerente']:
            flash('Acesso negado. Apenas administradores e gerentes podem criar usuários.', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            perfil = request.form['perfil']
            
            if Usuario.query.filter_by(email=email).first():
                flash('Email já cadastrado', 'error')
                return redirect(url_for('novo_usuario_empresa'))
            
            novo_usuario = Usuario(
                nome=nome,
                email=email,
                senha=senha,
                perfil=perfil,
                empresa_id=current_user.empresa_id
            )
            
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Usuário criado com sucesso', 'success')
            return redirect(url_for('listar_usuarios'))
        
        return render_template('novo_usuario_empresa.html')
    except Exception as e:
        app.logger.error(f'Erro ao criar usuário: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao criar o usuário', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/venda/<int:venda_id>/excluir', methods=['POST'])
@login_required
def excluir_venda(venda_id):
    try:
        venda = Venda.query.get_or_404(venda_id)
        produto = Produto.query.get_or_404(venda.produto_id)
        
        if produto.empresa_id != current_user.empresa_id:
            flash('Acesso negado. Você não pode excluir vendas de produtos de outras empresas.', 'error')
            return redirect(url_for('listar_vendas'))
        
        produto.quantidade += venda.quantidade
        db.session.delete(venda)
        db.session.commit()
        flash('Venda excluída com sucesso', 'success')
        return redirect(url_for('listar_vendas'))
    except Exception as e:
        app.logger.error(f'Erro ao excluir venda: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao excluir a venda', 'error')
        return redirect(url_for('listar_vendas'))

@app.route('/eventos/novo')
@login_required
def novo_evento_eventos():
    if request.method == 'POST':
        nome = request.form['nome']
        data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
        hora_inicio = datetime.strptime(request.form['hora_inicio'], '%H:%M').time()
        hora_fim = datetime.strptime(request.form['hora_fim'], '%H:%M').time()
        
        evento = Evento(
            nome=nome, 
            data_inicio=data, 
            data_fim=data + timedelta(hours=hora_fim.hour - hora_inicio.hour, minutes=hora_fim.minute - hora_inicio.minute),
            empresa_id=current_user.empresa_id
        )
        
        db.session.add(evento)
        db.session.commit()
        
        flash('Evento criado com sucesso!', 'success')
        return redirect(url_for('visualizar_evento', evento_id=evento.id))
    
    data_atual = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')
    
    return render_template('novo_evento_eventos.html', data_atual=data_atual, hora_atual=hora_atual)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/usuarios/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(usuario_id):
    try:
        if current_user.perfil not in ['admin', 'gerente']:
            flash('Acesso negado. Apenas administradores e gerentes podem editar usuários.', 'error')
            return redirect(url_for('index'))
        
        usuario = Usuario.query.get_or_404(usuario_id)
        
        if usuario.empresa_id != current_user.empresa_id:
            flash('Acesso negado. Você não pode editar usuários de outras empresas.', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if request.method == 'POST':
            usuario.nome = request.form['nome']
            usuario.email = request.form['email']
            usuario.perfil = request.form['perfil']
            
            if 'senha' in request.form and request.form['senha']:
                usuario.set_password(request.form['senha'])
            
            if 'foto' in request.files:
                foto = request.files['foto']
                if foto and allowed_file(foto.filename):
                    filename = secure_filename(foto.filename)
                    foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    usuario.foto = filename
            
            db.session.commit()
            flash('Usuário atualizado com sucesso', 'success')
            return redirect(url_for('listar_usuarios'))
        
        return render_template('editar_usuario.html', usuario=usuario)
    except Exception as e:
        app.logger.error(f'Erro ao editar usuário: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao editar o usuário', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/usuarios/<int:usuario_id>/excluir', methods=['POST'])
@login_required
def excluir_usuario(usuario_id):
    try:
        if current_user.perfil not in ['admin', 'gerente']:
            flash('Acesso negado. Apenas administradores e gerentes podem excluir usuários.', 'error')
            return redirect(url_for('index'))
        
        usuario = Usuario.query.get_or_404(usuario_id)
        
        if usuario.empresa_id != current_user.empresa_id:
            flash('Acesso negado. Você não pode excluir usuários de outras empresas.', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if usuario == current_user:
            flash('Você não pode excluir seu próprio usuário', 'error')
            return redirect(url_for('listar_usuarios'))
        
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuário excluído com sucesso', 'success')
        return redirect(url_for('listar_usuarios'))
    except Exception as e:
        app.logger.error(f'Erro ao excluir usuário: {str(e)}')
        db.session.rollback()
        flash('Ocorreu um erro ao excluir o usuário', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/empresas')
@login_required
def listar_empresas():
    # Verificar se o usuário tem permissão (admin)
    if current_user.perfil != 'admin':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    empresas = Empresa.query.order_by(Empresa.nome).all()
    return render_template('listar_empresas.html', empresas=empresas)

@app.route('/empresas/nova', methods=['GET', 'POST'])
@login_required
def nova_empresa():
    # Verificar se o usuário tem permissão (admin)
    if current_user.perfil != 'admin':
        flash('Você não tem permissão para criar empresas.', 'danger')
        return redirect(url_for('listar_empresas'))
    
    if request.method == 'POST':
        try:
            # Criar nova empresa
            empresa = Empresa(
                nome=request.form['nome'],
                cnpj=request.form['cnpj'],
                cep=request.form['cep'],
                endereco=request.form['endereco'],
                numero=request.form['numero'],
                complemento=request.form.get('complemento', ''),
                bairro=request.form['bairro'],
                cidade=request.form['cidade'],
                estado=request.form['estado'],
                status='pendente',
                ativo=True
            )
            
            db.session.add(empresa)
            db.session.commit()
            
            flash('Empresa criada com sucesso!', 'success')
            return redirect(url_for('listar_empresas'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar empresa: {str(e)}', 'danger')
    
    return render_template('nova_empresa.html')

@app.route('/empresas/<int:empresa_id>')
@login_required
def visualizar_empresa(empresa_id):
    # Verificar se o usuário tem permissão (admin)
    if current_user.perfil != 'admin':
        flash('Você não tem permissão para visualizar empresas.', 'danger')
        return redirect(url_for('index'))
    
    empresa = Empresa.query.get_or_404(empresa_id)
    return render_template('visualizar_empresa.html', empresa=empresa)

@app.route('/empresa/<int:empresa_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_empresa(empresa_id):
    try:
        if current_user.perfil != 'admin':
            flash('Acesso negado. Apenas administradores podem editar empresas.', 'danger')
            return redirect(url_for('index'))
            
        empresa = Empresa.query.get_or_404(empresa_id)
        
        if request.method == 'POST':
            empresa.nome = request.form['nome']
            empresa.cnpj = request.form['cnpj']
            empresa.endereco = request.form['endereco']
            empresa.telefone = request.form['telefone']
            empresa.email = request.form['email']
            empresa.status = request.form['status']
            
            db.session.commit()
            flash('Empresa atualizada com sucesso!', 'success')
            return redirect(url_for('listar_empresas'))
            
        return render_template('editar_empresa.html', empresa=empresa)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao editar empresa: {str(e)}')
        flash('Erro ao editar empresa. Por favor, tente novamente.', 'danger')
        return redirect(url_for('listar_empresas'))

@app.route('/empresa/<int:empresa_id>/excluir', methods=['POST'])
@login_required
def excluir_empresa(empresa_id):
    try:
        if current_user.perfil != 'admin':
            flash('Acesso negado. Apenas administradores podem excluir empresas.', 'danger')
            return redirect(url_for('index'))
            
        empresa = Empresa.query.get_or_404(empresa_id)
        
        # Verificar se a empresa tem usuários, eventos, barracas ou produtos
        if empresa.usuarios or empresa.eventos or empresa.barracas or empresa.produtos:
            flash('Não é possível excluir a empresa pois ela possui dados associados.', 'danger')
            return redirect(url_for('listar_empresas'))
            
        db.session.delete(empresa)
        db.session.commit()
        flash('Empresa excluída com sucesso!', 'success')
        return redirect(url_for('listar_empresas'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao excluir empresa: {str(e)}')
        flash('Erro ao excluir empresa. Por favor, tente novamente.', 'danger')
        return redirect(url_for('listar_empresas'))

@app.route('/barracas/<int:barraca_id>')
@login_required
def visualizar_barraca(barraca_id):
    try:
        barraca = Barraca.query.get_or_404(barraca_id)
        
        # Verifica se a barraca pertence à empresa do usuário
        if barraca.evento.empresa_id != current_user.empresa_id:
            flash('Você não tem permissão para visualizar esta barraca.', 'danger')
            return redirect(url_for('listar_todas_barracas'))
            
        return render_template('visualizar_barraca.html', barraca=barraca)
        
    except Exception as e:
        flash('Erro ao visualizar barraca.', 'danger')
        app.logger.error(f'Erro ao visualizar barraca: {str(e)}')
        return redirect(url_for('listar_todas_barracas'))

@app.route('/barracas/<int:barraca_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_barraca(barraca_id):
    try:
        barraca = Barraca.query.get_or_404(barraca_id)
        if barraca.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        if request.method == 'POST':
            barraca.nome = request.form['nome']
            barraca.descricao = request.form['descricao']
            
            db.session.commit()
            flash('Barraca atualizada com sucesso!', 'success')
            return redirect(url_for('visualizar_evento', evento_id=barraca.evento_id))
            
        return render_template('editar_barraca.html', barraca=barraca)
    except Exception as e:
        app.logger.error(f'Erro ao editar barraca: {str(e)}')
        flash('Erro ao editar barraca', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/barracas/<int:barraca_id>/excluir', methods=['POST'])
@login_required
def excluir_barraca(barraca_id):
    try:
        barraca = Barraca.query.get_or_404(barraca_id)
        if barraca.empresa_id != current_user.empresa_id:
            flash('Acesso negado', 'error')
            return redirect(url_for('listar_eventos'))
            
        evento_id = barraca.evento_id
        db.session.delete(barraca)
        db.session.commit()
        flash('Barraca excluída com sucesso!', 'success')
        return redirect(url_for('visualizar_evento', evento_id=evento_id))
    except Exception as e:
        app.logger.error(f'Erro ao excluir barraca: {str(e)}')
        flash('Erro ao excluir barraca', 'error')
        return redirect(url_for('listar_eventos'))

@app.route('/gestao')
@login_required
def gestao():
    try:
        if current_user.perfil != 'admin':
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('index'))
            
        # Obter contagens
        total_usuarios = Usuario.query.count()
        total_empresas = Empresa.query.count()
        total_eventos = Evento.query.count()
            
        return render_template('gestao.html',
                             total_usuarios=total_usuarios,
                             total_empresas=total_empresas,
                             total_eventos=total_eventos)
    except Exception as e:
        flash('Erro ao acessar a página de gestão.', 'danger')
        app.logger.error(f'Erro na página de gestão: {str(e)}')
        return redirect(url_for('index'))

@app.route('/registrar_venda', methods=['POST'])
@login_required
def registrar_venda():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' not in session or not session['evento_ativo_id']:
            return jsonify({'success': False, 'message': 'Nenhum evento selecionado. Por favor, selecione um evento antes de registrar a venda.'}), 400
            
        data = request.get_json()
        carrinho = data.get('carrinho', {})
        formas_pagamento = data.get('formas_pagamento', [])
        
        if not carrinho or not formas_pagamento:
            return jsonify({'success': False, 'message': 'Dados incompletos para registrar a venda.'}), 400
        
        # Obter o usuário atual
        usuario = Usuario.query.get(session['_user_id'])
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 400
        
        # Obter o evento ativo
        evento = Evento.query.get(session['evento_ativo_id'])
        if not evento:
            return jsonify({'success': False, 'message': 'Evento não encontrado.'}), 400
        
        # Calcular o total da venda
        total_venda = sum(item['preco'] * item['quantidade'] for item in carrinho.values())
        
        # Criar a venda
        venda = Venda(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            evento_id=evento.id,
            data_venda=datetime.now(),
            status='concluido',
            total=total_venda,
            cancelada=False
        )
        db.session.add(venda)
        db.session.flush()  # Para obter o ID da venda
        
        # Adicionar os itens da venda
        for produto_id, item in carrinho.items():
            produto = Produto.query.get(int(produto_id))
            if produto:
                item_venda = ItemVenda(
                    venda_id=venda.id,
                    produto_id=produto_id,
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco']
                )
                db.session.add(item_venda)
                
                # Atualizar o estoque
                produto.quantidade -= item['quantidade']
        
        # Adicionar as formas de pagamento
        for forma_pagamento in formas_pagamento:
            pagamento = Pagamento(
                venda_id=venda.id,
                forma_pagamento=forma_pagamento['metodo'],
                valor=forma_pagamento['valor']
            )
            db.session.add(pagamento)
        
        # Limpar o carrinho da sessão
        session['carrinho'] = {}
        
        # Commit todas as alterações
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Venda registrada com sucesso!',
            'venda_id': venda.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao registrar venda: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao registrar a venda: {str(e)}'}), 500

@app.route('/cancelar-item-venda/<int:venda_id>/<int:item_id>', methods=['POST'])
@login_required
def cancelar_item_venda(venda_id, item_id):
    try:
        # Buscar a venda e o item
        venda = Venda.query.get_or_404(venda_id)
        item = ItemVenda.query.get_or_404(item_id)
        
        # Verificar se o item pertence à venda
        if item.venda_id != venda_id:
            return jsonify({'success': False, 'message': 'Item não pertence a esta venda'}), 400
            
        # Verificar se a venda pertence à empresa do usuário
        if venda.empresa_id != current_user.empresa_id:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            
        # Verificar se o item já está cancelado
        if item.status == 'cancelado':
            return jsonify({'success': False, 'message': 'Item já está cancelado'}), 400
            
        # Buscar o produto
        produto = Produto.query.get(item.produto_id)
        if not produto:
            return jsonify({'success': False, 'message': 'Produto não encontrado'}), 404
            
        # Atualizar o estoque do produto
        produto.quantidade += 1  # Devolve uma unidade ao estoque
        
        # Atualizar o total da venda
        venda.total -= item.preco_unitario
        
        # Se a quantidade do item for maior que 1, apenas decrementar
        if item.quantidade > 1:
            item.quantidade -= 1
        else:
            # Se a quantidade for 1, marcar o item como cancelado
            item.status = 'cancelado'
        
        # Verificar se todos os itens estão cancelados
        todos_cancelados = all(item.status == 'cancelado' for item in venda.itens_venda)
        alguns_cancelados = any(item.status == 'cancelado' for item in venda.itens_venda)
        
        # Atualizar o status da venda
        if todos_cancelados:
            venda.status = 'cancelada'
            venda.cancelada = True
        elif alguns_cancelados:
            venda.status = 'cancelamento_parcial'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item cancelado com sucesso',
            'venda_status': venda.status,
            'item_status': item.status
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao cancelar item da venda: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar item da venda: {str(e)}'
        }), 500

@app.route('/cancelar-venda/<int:venda_id>', methods=['POST'])
@login_required
def cancelar_venda(venda_id):
    try:
        # Buscar a venda
        venda = Venda.query.get_or_404(venda_id)
        
        # Verificar se a venda pertence à empresa do usuário
        if venda.empresa_id != current_user.empresa_id:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            
        # Buscar todos os itens da venda
        itens_venda = ItemVenda.query.filter_by(venda_id=venda_id).all()
        
        # Atualizar o estoque dos produtos
        for item in itens_venda:
            produto = Produto.query.get(item.produto_id)
            if produto:
                produto.quantidade += item.quantidade
        
        # Marcar a venda como cancelada
        venda.cancelada = True
        
        # Salvar as alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Venda cancelada com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao cancelar venda: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar venda: {str(e)}'
        }), 500

@app.route('/atualizar_vendas_existentes')
@login_required
def atualizar_vendas_existentes():
    try:
        # Buscar todas as vendas que não têm o campo cancelada definido
        vendas = Venda.query.filter(Venda.cancelada.is_(None)).all()
        
        # Atualizar cada venda
        for venda in vendas:
            venda.cancelada = False
        
        # Salvar as alterações
        db.session.commit()
        
        flash('Vendas atualizadas com sucesso!', 'success')
        return redirect(url_for('relatorio_vendas'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao atualizar vendas: {str(e)}')
        flash('Erro ao atualizar vendas', 'error')
        return redirect(url_for('relatorio_vendas'))

@app.route('/relatorios/estoque')
@login_required
def relatorio_estoque():
    try:
        # Verificar se há um evento selecionado
        if 'evento_ativo_id' not in session:
            flash('Selecione um evento primeiro', 'warning')
            return redirect(url_for('index'))
            
        # Obter parâmetros de filtro
        produto_nome = request.args.get('produto')
        status = request.args.get('status')
        barraca_id = request.args.get('barraca')
        
        # Construir a query base com agrupamento
        query = (db.session.query(
                    Produto.nome,
                    Produto.quantidade.label('quantidade_inicial'),
                    db.func.sum(case((Venda.cancelada.is_(True), ItemVenda.quantidade), else_=0)).label('quantidade_estornada'),
                    db.func.sum(case((Venda.cancelada.is_(False), ItemVenda.quantidade), else_=0)).label('quantidade_vendida')
                )
                .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)
                .outerjoin(Venda, ItemVenda.venda_id == Venda.id)
                .join(Barraca, Produto.barraca_id == Barraca.id)
                .filter(Produto.empresa_id == current_user.empresa_id)
                .filter(Produto.evento_id == session['evento_ativo_id'])
                .group_by(Produto.nome, Produto.quantidade))
        
        # Aplicar filtros
        if produto_nome:
            query = query.filter(Produto.nome.ilike(f'%{produto_nome}%'))
        if barraca_id:
            query = query.filter(Barraca.id == barraca_id)
        
        # Ordenar por nome do produto
        produtos_agrupados = query.order_by(Produto.nome).all()
        
        # Converter para lista de dicionários com propriedades necessárias
        produtos = []
        for nome, quantidade_inicial, quantidade_estornada, quantidade_vendida in produtos_agrupados:
            quantidade_estornada = quantidade_estornada or 0
            quantidade_vendida = quantidade_vendida or 0
            quantidade_atual = quantidade_inicial - quantidade_vendida + quantidade_estornada
            produtos.append({
                'nome': nome,
                'quantidade_inicial': quantidade_inicial,
                'quantidade_vendida': quantidade_vendida,
                'quantidade_estornada': quantidade_estornada,
                'estoque_baixo': quantidade_atual <= 5
            })
        
        # Filtrar por status em Python
        if status:
            if status == 'esgotado':
                produtos = [p for p in produtos if p['quantidade_inicial'] - p['quantidade_vendida'] + p['quantidade_estornada'] == 0]
            elif status == 'baixo':
                produtos = [p for p in produtos if p['quantidade_inicial'] - p['quantidade_vendida'] + p['quantidade_estornada'] <= 5 and p['quantidade_inicial'] - p['quantidade_vendida'] + p['quantidade_estornada'] > 0]
            elif status == 'normal':
                produtos = [p for p in produtos if p['quantidade_inicial'] - p['quantidade_vendida'] + p['quantidade_estornada'] > 5]
        
        # Obter o evento ativo e as barracas para o filtro
        evento_ativo = Evento.query.get(session['evento_ativo_id'])
        barracas = Barraca.query.filter_by(
            evento_id=session['evento_ativo_id'],
            empresa_id=current_user.empresa_id
        ).order_by(Barraca.nome).all()
        
        return render_template('relatorio_estoque.html', 
                             produtos=produtos,
                             evento_ativo=evento_ativo,
                             barracas=barracas)
                             
    except Exception as e:
        app.logger.error(f'Erro ao gerar relatório de estoque: {str(e)}')
        flash('Erro ao gerar relatório de estoque', 'error')
        return redirect(url_for('index'))

@app.route('/relatorio_estoque_pdf')
@login_required
def relatorio_estoque_pdf():
    try:
        if 'evento_ativo_id' not in session:
            flash('Selecione um evento para gerar o relatório em PDF.', 'info')
            return redirect(url_for('index'))
            
        evento_id = session['evento_ativo_id']
        barraca_id = request.args.get('barraca')
        produto_nome = request.args.get('produto')
        status = request.args.get('status')
        
        # Buscar produtos com quantidade vendida e estornada
        query = db.session.query(
            Produto,
            db.func.coalesce(db.func.sum(case((Venda.cancelada.is_(True), ItemVenda.quantidade), else_=0)), 0).label('quantidade_estornada'),
            db.func.coalesce(db.func.sum(case((Venda.cancelada.is_(False), ItemVenda.quantidade), else_=0)), 0).label('quantidade_vendida')
        )\
        .select_from(Produto)\
        .join(Barraca, Produto.barraca_id == Barraca.id)\
        .join(Evento, Barraca.evento_id == Evento.id)\
        .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)\
        .outerjoin(Venda, ItemVenda.venda_id == Venda.id)\
        .filter(
            Evento.id == evento_id,
            Evento.empresa_id == current_user.empresa_id
        )
        
        # Aplicar filtros
        if barraca_id:
            query = query.filter(Produto.barraca_id == barraca_id)
        if produto_nome:
            query = query.filter(Produto.nome.ilike(f'%{produto_nome}%'))
        
        produtos = query.group_by(Produto.id)\
            .order_by(Produto.nome)\
            .all()
        
        # Preparar dados para o PDF
        produtos_com_quantidade = []
        for produto, quantidade_estornada, quantidade_vendida in produtos:
            quantidade_atual = produto.quantidade - quantidade_vendida + quantidade_estornada
            
            # Aplicar filtro de status
            if status:
                if status == 'esgotado' and quantidade_atual != 0:
                    continue
                elif status == 'baixo' and (quantidade_atual > 5 or quantidade_atual == 0):
                    continue
                elif status == 'normal' and quantidade_atual <= 5:
                    continue
            
            produtos_com_quantidade.append({
                'produto': produto,
                'quantidade_vendida': quantidade_vendida,
                'quantidade_estornada': quantidade_estornada,
                'quantidade_atual': quantidade_atual
            })
        
        # Gerar PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=landscape(letter))
        
        # Configurar margens (1cm = 28 pontos)
        margem = 28
        largura_pagina = landscape(letter)[0]
        altura_pagina = landscape(letter)[1]
        
        # Configurar o PDF
        p.setTitle("Relatório de Estoque")
        p.setFont("Helvetica-Bold", 16)
        p.drawString(margem, altura_pagina - margem - 20, "Relatório de Estoque")
        
        # Informações do evento
        evento = Evento.query.get(evento_id)
        p.setFont("Helvetica", 12)
        p.drawString(margem, altura_pagina - margem - 50, f"Evento: {evento.nome}")
        if barraca_id:
            barraca = Barraca.query.get(barraca_id)
            p.drawString(margem, altura_pagina - margem - 70, f"Barraca: {barraca.nome}")
        
        # Cabeçalho da tabela
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margem, altura_pagina - margem - 100, "Produto")
        p.drawString(margem + 200, altura_pagina - margem - 100, "Estoque Atual")
        p.drawString(margem + 300, altura_pagina - margem - 100, "Vendidos")
        p.drawString(margem + 400, altura_pagina - margem - 100, "Estornados")
        p.drawString(margem + 500, altura_pagina - margem - 100, "Status")
        
        # Dados da tabela
        p.setFont("Helvetica", 10)
        y = altura_pagina - margem - 120
        
        # Totais
        total_estoque = 0
        total_vendidos = 0
        total_estornados = 0
        
        for item in produtos_com_quantidade:
            if y < margem + 50:  # Nova página se necessário
                p.showPage()
                y = altura_pagina - margem - 20
                # Redesenhar cabeçalho
                p.setFont("Helvetica-Bold", 10)
                p.drawString(margem, y, "Produto")
                p.drawString(margem + 200, y, "Estoque Atual")
                p.drawString(margem + 300, y, "Vendidos")
                p.drawString(margem + 400, y, "Estornados")
                p.drawString(margem + 500, y, "Status")
                y = altura_pagina - margem - 40
                p.setFont("Helvetica", 10)
            
            # Desenhar linha
            p.drawString(margem, y, item['produto'].nome)
            p.drawString(margem + 200, y, str(item['produto'].quantidade))
            p.drawString(margem + 300, y, str(item['quantidade_vendida']))
            p.drawString(margem + 400, y, str(item['quantidade_estornada']))
            
            # Status
            if item['quantidade_atual'] == 0:
                status = "Esgotado"
            elif item['quantidade_atual'] <= 5:
                status = "Estoque Baixo"
            else:
                status = "Normal"
            p.drawString(margem + 500, y, status)
            
            # Atualizar totais
            total_estoque += item['produto'].quantidade
            total_vendidos += item['quantidade_vendida']
            total_estornados += item['quantidade_estornada']
            
            y -= 20
        
        # Adicionar linha de totalizadores
        y -= 20  # Espaço extra antes dos totais
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margem, y, "Totais:")
        p.drawString(margem + 200, y, str(total_estoque))
        p.drawString(margem + 300, y, str(total_vendidos))
        p.drawString(margem + 400, y, str(total_estornados))
        
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"relatorio_estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar PDF do relatório de estoque: {str(e)}")
        flash('Erro ao gerar PDF do relatório. Por favor, tente novamente.', 'error')
        return redirect(url_for('relatorio_estoque'))

@app.route('/remover_fundo', methods=['POST'])
@login_required
def remover_fundo():
    try:
        data = request.get_json()
        imagem_base64 = data.get('imagem')
        
        if not imagem_base64:
            return jsonify({'error': 'Nenhuma imagem fornecida'}), 400
            
        # Decodificar a imagem base64
        try:
            imagem_bytes = base64.b64decode(imagem_base64.split(',')[1])
        except Exception as e:
            return jsonify({'error': 'Formato de imagem inválido'}), 400
        
        # Configurar a requisição para a API do remove.bg
        headers = {
            'X-Api-Key': 'YOUR-API-KEY-HERE',  # Substitua pela sua chave de API do remove.bg
        }
        
        files = {
            'image_file': ('imagem.jpg', BytesIO(imagem_bytes)),
        }
        
        # Fazer a requisição para a API
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            headers=headers,
            files=files,
            data={
                'size': 'auto',
                'format': 'auto',
                'bg_color': 'white'
            }
        )
        
        if response.status_code == 200:
            # Converter a resposta para base64
            imagem_sem_fundo = base64.b64encode(response.content).decode('utf-8')
            return jsonify({
                'success': True,
                'imagem': f'data:image/png;base64,{imagem_sem_fundo}'
            })
        else:
            app.logger.error(f'Erro na API remove.bg: {response.text}')
            return jsonify({
                'error': f'Erro ao remover o fundo da imagem: {response.text}'
            }), 500
            
    except Exception as e:
        app.logger.error(f'Erro ao remover fundo: {str(e)}')
        return jsonify({
            'error': 'Erro ao processar a imagem',
            'details': str(e)
        }), 500

@app.route('/relatorio_vendas_pdf')
@login_required
def relatorio_vendas_pdf():
    try:
        # Verifica se há um evento ativo
        evento_id = session.get('evento_ativo_id')
        if not evento_id:
            flash('Selecione um evento primeiro.', 'warning')
            return redirect(url_for('index'))
        
        # Obtém os parâmetros de filtro
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        barraca_id = request.args.get('barraca')
        forma_pagamento = request.args.get('forma_pagamento')
        vendedor_id = request.args.get('vendedor')
        status = request.args.get('status')
        
        # Busca as vendas
        vendas = Venda.query.filter_by(
            empresa_id=current_user.empresa_id,
            evento_id=evento_id
        ).order_by(Venda.data_venda.desc()).all()
        
        if not vendas:
            flash('Nenhuma venda encontrada.', 'info')
            return redirect(url_for('relatorio_vendas'))
        
        # Prepara os dados para o PDF
        data = []
        for venda in vendas:
            # Aplica filtros básicos
            if data_inicio and venda.data_venda < datetime.strptime(data_inicio, '%Y-%m-%d'):
                continue
            if data_fim and venda.data_venda > datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1):
                continue
            if vendedor_id and str(venda.usuario_id) != vendedor_id:
                continue
            if status:
                if status == 'ativa' and venda.cancelada:
                    continue
                if status == 'cancelada' and not venda.cancelada:
                    continue
            
            # Processa os itens da venda
            for item in venda.itens_venda:
                # Filtra por barraca
                if barraca_id and str(item.produto.barraca_id) != barraca_id:
                    continue
                
                # Filtra por forma de pagamento
                if forma_pagamento:
                    tem_pagamento = False
                    for pagamento in venda.pagamentos:
                        if pagamento.forma_pagamento == forma_pagamento:
                            tem_pagamento = True
                            break
                    if not tem_pagamento:
                        continue
                
                # Adiciona o item aos dados
                data.append({
                    'data': venda.data_venda.strftime('%d/%m/%Y %H:%M'),
                    'produto': item.produto.nome,
                    'barraca': item.produto.barraca.nome,
                    'quantidade': item.quantidade,
                    'valor_unitario': f'R$ {item.preco_unitario:.2f}',
                    'valor_total': f'R$ {item.preco_unitario * item.quantidade:.2f}',
                    'status': 'Cancelada' if venda.cancelada else 'Ativa',
                    'forma_pagamento': venda.pagamentos[0].forma_pagamento if venda.pagamentos else 'N/A',
                    'vendedor': venda.usuario.nome
                })
        
        if not data:
            flash('Nenhuma venda encontrada para os filtros selecionados.', 'info')
            return redirect(url_for('relatorio_vendas'))
        
        # Gera o PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        
        # Título
        evento = Evento.query.get(evento_id)
        elements.append(Paragraph(f'Relatório de Vendas - {evento.nome}', title_style))
        
        # Adiciona informações dos filtros
        filtros = []
        if data_inicio:
            filtros.append(f"Data Início: {datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')}")
        if data_fim:
            filtros.append(f"Data Fim: {datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')}")
        if barraca_id:
            barraca = Barraca.query.get(barraca_id)
            filtros.append(f"Barraca: {barraca.nome}")
        if forma_pagamento:
            filtros.append(f"Forma de Pagamento: {forma_pagamento}")
        if vendedor_id:
            vendedor = Usuario.query.get(vendedor_id)
            filtros.append(f"Vendedor: {vendedor.nome}")
        if status:
            filtros.append(f"Status: {status}")
        
        if filtros:
            elements.append(Paragraph("Filtros aplicados:", styles['Normal']))
            for filtro in filtros:
                elements.append(Paragraph(filtro, styles['Normal']))
            elements.append(Spacer(1, 20))
        
        # Cabeçalho da tabela
        headers = ['Data', 'Produto', 'Barraca', 'Qtd', 'Valor Unit.', 'Valor Total', 'Status', 'Forma Pag.', 'Vendedor']
        table_data = [headers]
        
        # Dados da tabela
        for venda in data:
            row = [
                venda['data'],
                venda['produto'],
                venda['barraca'],
                str(venda['quantidade']),
                venda['valor_unitario'],
                venda['valor_total'],
                venda['status'],
                venda['forma_pagamento'],
                venda['vendedor']
            ]
            table_data.append(row)
        
        # Cria a tabela
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        
        # Adiciona totais
        total_vendas = sum(venda['quantidade'] for venda in data)
        total_valor = sum(float(venda['valor_total'].replace('R$ ', '').replace(',', '.')) for venda in data)
        
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f'Total de Itens Vendidos: {total_vendas}', styles['Normal']))
        elements.append(Paragraph(f'Valor Total: R$ {total_valor:.2f}', styles['Normal']))
        
        # Adiciona data e hora da geração
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f'Relatório gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', styles['Normal']))
        
        # Gera o PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Retorna o PDF
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_vendas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f'Erro ao gerar PDF do relatório de vendas: {str(e)}')
        flash('Erro ao gerar PDF do relatório. Por favor, tente novamente.', 'error')
        return redirect(url_for('relatorio_vendas'))

if __name__ == '__main__':
    app.run(debug=True) 