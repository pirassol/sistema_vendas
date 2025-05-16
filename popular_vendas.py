from app import app, db, Venda, ItemVenda, Pagamento, Produto, Evento, Usuario
from datetime import datetime, timedelta
import random

def gerar_vendas():
    with app.app_context():
        # Obter todos os produtos disponíveis
        produtos = Produto.query.all()
        if not produtos:
            print("Nenhum produto encontrado no banco de dados.")
            return

        # Obter todos os eventos
        eventos = Evento.query.all()
        if not eventos:
            print("Nenhum evento encontrado no banco de dados.")
            return

        # Obter todos os usuários
        usuarios = Usuario.query.all()
        if not usuarios:
            print("Nenhum usuário encontrado no banco de dados.")
            return

        # Número de vendas a serem geradas
        num_vendas = 50

        # Formas de pagamento possíveis
        formas_pagamento = ['dinheiro', 'credito', 'debito', 'pix']

        # Gerar vendas
        for _ in range(num_vendas):
            # Selecionar um evento aleatório
            evento = random.choice(eventos)
            
            # Selecionar um usuário aleatório
            usuario = random.choice(usuarios)
            
            # Data da venda (últimos 30 dias)
            dias_aleatorios = random.randint(0, 30)
            data_venda = datetime.now() - timedelta(days=dias_aleatorios)
            
            # Criar a venda
            venda = Venda(
                empresa_id=evento.empresa_id,
                usuario_id=usuario.id,
                data_venda=data_venda,
                evento_id=evento.id,
                cancelada=False,
                total=0.0
            )
            db.session.add(venda)
            db.session.flush()  # Para obter o ID da venda
            
            # Selecionar produtos aleatórios para a venda
            num_produtos = random.randint(1, 5)  # Entre 1 e 5 produtos por venda
            produtos_venda = random.sample(produtos, min(num_produtos, len(produtos)))
            
            total_venda = 0
            
            # Adicionar itens à venda
            for produto in produtos_venda:
                quantidade = random.randint(1, 3)  # Entre 1 e 3 unidades de cada produto
                
                # Criar um item individual para cada unidade
                for i in range(quantidade):
                    item = ItemVenda(
                        venda_id=venda.id,
                        produto_id=produto.id,
                        quantidade=1,  # Cada item tem quantidade 1
                        preco_unitario=produto.preco,
                        status='pago'
                    )
                    db.session.add(item)
                    db.session.flush()  # Para obter o ID do item
                    
                    total_venda += produto.preco
                    print(f"  Item {item.id} adicionado: {produto.nome}")
            
            # Atualizar o total da venda
            venda.total = total_venda
            
            # Adicionar pagamento
            forma_pagamento = random.choice(formas_pagamento)
            pagamento = Pagamento(
                venda_id=venda.id,
                forma_pagamento=forma_pagamento,
                valor=total_venda
            )
            
            # Se for pagamento em dinheiro, adicionar valor recebido e troco
            if forma_pagamento == 'dinheiro':
                # Arredondar para cima para o próximo múltiplo de 5
                valor_recebido = ((total_venda + 4) // 5) * 5
                pagamento.valor_recebido = valor_recebido
                pagamento.troco = valor_recebido - total_venda
            
            db.session.add(pagamento)
            
            try:
                db.session.commit()
                print(f"Venda {venda.id} criada com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao criar venda: {str(e)}")

def popular_vendas():
    with app.app_context():
        try:
            print("Populando banco de dados com vendas de teste...")
            
            # Buscar dados necessários
            usuarios = Usuario.query.all()
            eventos = Evento.query.all()
            produtos = Produto.query.all()
            
            if not usuarios or not eventos or not produtos:
                print("Erro: Necessário ter usuários, eventos e produtos cadastrados!")
                return
            
            # Criar algumas vendas de teste
            formas_pagamento = ['dinheiro', 'cartao_credito', 'cartao_debito', 'pix']
            data_base = datetime.now() - timedelta(days=30)  # Últimos 30 dias
            
            for i in range(20):  # Criar 20 vendas
                # Dados aleatórios para a venda
                usuario = random.choice(usuarios)
                evento = random.choice(eventos)
                data_venda = data_base + timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Criar a venda
                venda = Venda(
                    empresa_id=usuario.empresa_id,
                    usuario_id=usuario.id,
                    evento_id=evento.id,
                    data_venda=data_venda,
                    status='pago'
                )
                db.session.add(venda)
                db.session.flush()  # Para obter o ID da venda
                
                # Adicionar 1 a 5 itens na venda
                total_venda = 0
                for _ in range(random.randint(1, 5)):
                    produto = random.choice(produtos)
                    quantidade = random.randint(1, 3)
                    preco_unitario = produto.preco
                    
                    item = ItemVenda(
                        venda_id=venda.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=preco_unitario,
                        status='pago'
                    )
                    total_venda += quantidade * preco_unitario
                    db.session.add(item)
                
                # Atualizar o total da venda
                venda.total = total_venda
                
                # Criar pagamento
                forma_pagamento = random.choice(formas_pagamento)
                pagamento = Pagamento(
                    venda_id=venda.id,
                    forma_pagamento=forma_pagamento,
                    valor=total_venda
                )
                
                # Se for dinheiro, adicionar valor recebido e troco
                if forma_pagamento == 'dinheiro':
                    valor_recebido = total_venda + random.randint(0, 50)  # Algum troco
                    pagamento.valor_recebido = valor_recebido
                    pagamento.troco = valor_recebido - total_venda
                
                db.session.add(pagamento)
            
            # Commit das alterações
            db.session.commit()
            print("Dados populados com sucesso!")
            print(f"- 20 vendas criadas")
            print(f"- Vendas distribuídas nos últimos 30 dias")
            print(f"- Diferentes formas de pagamento e quantidades")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro durante a população dos dados: {str(e)}")

if __name__ == '__main__':
    print("Iniciando geração de vendas...")
    gerar_vendas()
    print("Processo de geração de vendas concluído!")
    popular_vendas() 