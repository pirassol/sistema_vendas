from app import app, db, Evento, Barraca, Produto, Empresa
from datetime import datetime, timedelta
import random

def limpar_dados():
    with app.app_context():
        try:
            # Remover todos os produtos
            Produto.query.delete()
            # Remover todas as barracas
            Barraca.query.delete()
            # Remover todos os eventos
            Evento.query.delete()
            # Commit das alterações
            db.session.commit()
            print("Dados anteriores removidos com sucesso!")
        except Exception as e:
            print(f"Erro ao limpar dados: {e}")
            db.session.rollback()

def criar_empresa_admin():
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
    return empresa

def popular_dados():
    with app.app_context():
        # Limpar dados existentes
        limpar_dados()
        
        # Criar ou obter a empresa de administração
        empresa = criar_empresa_admin()

        # Lista de nomes para eventos
        eventos_nomes = [
            "Feira de Artesanato",
            "Festival Gastronômico",
            "Exposição de Tecnologia"
        ]

        # Lista de nomes para barracas
        barracas_nomes = [
            "Barraca do João",
            "Cantina da Maria",
            "Loja do Seu José",
            "Quiosque da Ana",
            "Tenda do Pedro"
        ]

        # Lista de produtos com preços
        produtos = [
            ("Cachorro Quente", 15.00),
            ("Refrigerante", 8.00),
            ("Água Mineral", 5.00),
            ("Pipoca", 10.00),
            ("Churros", 12.00),
            ("Sorvete", 15.00),
            ("Bolo", 20.00),
            ("Café", 7.00),
            ("Suco Natural", 12.00),
            ("Salgadinho", 8.00)
        ]

        try:
            # Criar eventos
            for i, nome in enumerate(eventos_nomes):
                data_inicio = datetime.now() + timedelta(days=i*7)  # Eventos com 7 dias de intervalo
                data_fim = data_inicio + timedelta(days=1)  # Evento dura 1 dia
                evento = Evento(
                    empresa_id=empresa.id,
                    nome=nome,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    status='ativo'
                )
                db.session.add(evento)
                db.session.commit()
                print(f"Evento criado: {nome}")

                # Criar barracas para cada evento
                for barraca_nome in barracas_nomes:
                    barraca = Barraca(
                        empresa_id=empresa.id,
                        nome=barraca_nome,
                        descricao=f"Barraca de {barraca_nome} no evento {nome}",
                        evento_id=evento.id
                    )
                    db.session.add(barraca)
                    db.session.commit()
                    print(f"  Barraca criada: {barraca_nome}")

                    # Criar produtos para cada barraca
                    for produto_nome, preco in produtos:
                        produto = Produto(
                            empresa_id=empresa.id,
                            nome=produto_nome,
                            preco=preco,
                            quantidade=random.randint(50, 200),
                            evento_id=evento.id,
                            barraca_id=barraca.id
                        )
                        db.session.add(produto)
                        db.session.commit()
                        print(f"    Produto criado: {produto_nome}")
            
            print("\nTodos os dados foram inseridos com sucesso!")
        
        except Exception as e:
            print(f"Erro ao popular dados: {e}")
            db.session.rollback()

if __name__ == '__main__':
    popular_dados() 