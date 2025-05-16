from app import app, db, Empresa
from datetime import datetime

def verificar_empresa():
    with app.app_context():
        empresa = Empresa.query.filter_by(cnpj='00000000000000').first()
        if not empresa:
            print("Criando empresa de administração...")
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
            db.session.add(empresa)
            db.session.commit()
            print("Empresa de administração criada com sucesso!")
        else:
            print(f"Empresa encontrada: {empresa.nome} (CNPJ: {empresa.cnpj})")
            print(f"Status: {empresa.status}")
            print(f"Ativo: {empresa.ativo}")

if __name__ == '__main__':
    verificar_empresa() 