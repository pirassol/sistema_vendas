from app import app, db, Usuario, Empresa
from datetime import datetime

def criar_admin():
    with app.app_context():
        # Primeiro, criar uma empresa padrão para o admin
        empresa = Empresa(
            nome='Administração do Sistema',
            cnpj='00000000000000',
            cep='00000000',
            endereco='Sistema',
            numero='0',
            complemento='',
            bairro='Sistema',
            cidade='Sistema',
            estado='SP',
            status='aprovado',
            ativo=True
        )
        
        # Verificar se a empresa já existe
        empresa_existente = Empresa.query.filter_by(cnpj='00000000000000').first()
        if not empresa_existente:
            db.session.add(empresa)
            db.session.commit()
            print("Empresa de administração criada com sucesso!")
        else:
            empresa = empresa_existente
            print("Empresa de administração já existe.")

        # Criar usuário admin
        admin = Usuario(
            nome='Administrador',
            email='admin@sistema.com',
            perfil='admin',
            empresa_id=empresa.id,
            ativo=True
        )
        admin.set_password('admin123')  # Senha inicial: admin123

        # Verificar se o admin já existe
        admin_existente = Usuario.query.filter_by(email='admin@sistema.com').first()
        if not admin_existente:
            db.session.add(admin)
            db.session.commit()
            print("\nUsuário administrador criado com sucesso!")
            print("Email: admin@sistema.com")
            print("Senha: admin123")
        else:
            print("\nUsuário administrador já existe.")
            print("Email: admin@sistema.com")
            print("Senha: admin123")

if __name__ == '__main__':
    criar_admin() 